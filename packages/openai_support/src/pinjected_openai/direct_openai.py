"""Direct OpenAI API implementation with StructuredLLM support.

This module provides direct OpenAI API access, bypassing OpenRouter's 5% fee.
It includes proper GPT-5 support with max_completion_tokens parameter handling.
"""

import json
from typing import Any, Protocol, TYPE_CHECKING

import PIL.Image
from openai import AsyncOpenAI
from pinjected import design, injected, instance
from pydantic import BaseModel, ValidationError

if TYPE_CHECKING:
    from pinjected_openai.openrouter.instances import StructuredLLM


class LoggerProtocol(Protocol):
    def debug(self, message: str) -> None: ...
    def info(self, message: str) -> None: ...
    def warning(self, message: str) -> None: ...
    def error(self, message: str) -> None: ...
    def success(self, message: str) -> None: ...


class ASllmOpenaiProtocol(Protocol):
    """Protocol for direct OpenAI structured LLM."""

    async def __call__(
        self,
        text: str,
        model: str = "gpt-4o",
        images: list[PIL.Image.Image] | None = None,
        response_format: type[BaseModel] | None = None,
        max_tokens: int = 8192,
        temperature: float = 0.7,
        **kwargs,
    ) -> Any: ...


class AStructuredLlmOpenaiProtocol(Protocol):
    """Protocol for StructuredLLM-compatible OpenAI wrapper."""

    async def __call__(
        self,
        text: str,
        images: list[PIL.Image.Image] | None = None,
        response_format: type[BaseModel] | None = None,
        model: str = "gpt-4o",
        **kwargs,
    ) -> Any: ...


def is_gpt5_model(model: str) -> bool:
    """Check if the model is a GPT-5 variant."""
    return "gpt-5" in model.lower() or "gpt5" in model.lower()


def convert_pil_to_base64(image: PIL.Image.Image) -> str:
    """Convert PIL image to base64 string for OpenAI API."""
    import base64
    import io

    # Convert PIL image to bytes
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    img_bytes = buffered.getvalue()

    # Encode to base64
    img_base64 = base64.b64encode(img_bytes).decode("utf-8")
    return f"data:image/png;base64,{img_base64}"


@injected(protocol=ASllmOpenaiProtocol)
async def a_sllm_openai(  # noqa: PINJ045
    async_openai_client: AsyncOpenAI,
    logger: LoggerProtocol,
    /,
    text: str,
    model: str = "gpt-4o",
    images: list[PIL.Image.Image] | None = None,
    response_format: type[BaseModel] | None = None,
    max_tokens: int = 8192,
    temperature: float = 0.7,
    **kwargs,
) -> Any:
    """
    Direct OpenAI API structured LLM implementation.

    This function bypasses OpenRouter and calls OpenAI directly, avoiding the 5% fee.
    It properly handles GPT-5 models by using max_completion_tokens instead of max_tokens.

    Args:
        text: The prompt text
        model: OpenAI model name (e.g., "gpt-4o", "gpt-5-nano", "gpt-5")
        images: Optional list of PIL images to include
        response_format: Optional Pydantic BaseModel for structured output
        max_tokens: Maximum tokens for completion (transformed to max_completion_tokens for GPT-5)
        temperature: Temperature for sampling
        **kwargs: Additional OpenAI API parameters

    Returns:
        Parsed response according to response_format, or raw text if no format specified
    """

    logger.debug(
        f"a_sllm_openai called with model={model}, response_format={response_format}"
    )

    # Build the messages
    messages = []

    # Build content for the user message
    content = [{"type": "text", "text": text}]

    # Add images if provided
    if images:
        for img in images:
            img_base64 = convert_pil_to_base64(img)
            content.append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": img_base64,
                        "detail": kwargs.pop("detail", "auto"),
                    },
                }
            )

    messages.append(
        {
            "role": "user",
            "content": content if images else text,  # Use simple text if no images
        }
    )

    # Build the API call parameters
    api_params = {
        "model": model,
        "messages": messages,
        **kwargs,  # Pass through any additional parameters
    }

    # GPT-5 models only support temperature=1.0
    if not is_gpt5_model(model):
        api_params["temperature"] = temperature
    # GPT-5 only supports default temperature (1.0)
    elif temperature != 1.0:
        logger.debug(
            f"GPT-5 models only support temperature=1.0, ignoring temperature={temperature}"
        )

    # Handle token parameter based on model
    if is_gpt5_model(model):
        # GPT-5 models require max_completion_tokens
        # Ensure sufficient tokens for reasoning + output
        token_value = max(max_tokens, 500)  # Minimum 500 for GPT-5
        api_params["max_completion_tokens"] = token_value
        logger.debug(
            f"Using max_completion_tokens={token_value} for GPT-5 model {model}"
        )
    else:
        # Other models use max_tokens
        api_params["max_tokens"] = max_tokens
        logger.debug(f"Using max_tokens={max_tokens} for model {model}")

    # Handle structured output if requested
    if response_format is not None and issubclass(response_format, BaseModel):
        logger.debug(f"Using structured output with {response_format.__name__}")

        # Get the JSON schema and ensure it's properly formatted for OpenAI
        schema = response_format.model_json_schema()
        # OpenAI requires additionalProperties: false for strict mode
        schema["additionalProperties"] = False
        # OpenAI requires 'required' field to list ALL properties (even with defaults)
        if "properties" in schema:
            # OpenAI strict mode requires ALL properties to be in required array
            schema["required"] = list(schema["properties"].keys())

        # Use OpenAI's structured output feature
        api_params["response_format"] = {
            "type": "json_schema",
            "json_schema": {
                "name": response_format.__name__,
                "schema": schema,
                "strict": True,
            },
        }

        try:
            # Make the API call
            response = await async_openai_client.chat.completions.create(**api_params)

            # Extract the content
            content = response.choices[0].message.content

            # Log usage information
            if response.usage:
                logger.info(f"Token usage: {response.usage.model_dump()}")
                if hasattr(response.usage, "completion_tokens_details"):
                    details = response.usage.completion_tokens_details
                    if (
                        hasattr(details, "reasoning_tokens")
                        and details.reasoning_tokens
                    ):
                        logger.info(
                            f"GPT-5 reasoning tokens: {details.reasoning_tokens}"
                        )

            # Parse the JSON response
            try:
                parsed_json = json.loads(content)
                result = response_format(**parsed_json)
                logger.success(
                    f"Successfully parsed response as {response_format.__name__}"
                )
                return result
            except (json.JSONDecodeError, ValidationError) as e:
                logger.error(f"Failed to parse structured response: {e}")
                logger.debug(f"Raw content: {content}")
                raise

        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise

    else:
        # No structured output requested
        logger.debug("Using unstructured text output")

        try:
            response = await async_openai_client.chat.completions.create(**api_params)

            # Log usage information
            if response.usage:
                logger.info(f"Token usage: {response.usage.model_dump()}")
                if hasattr(response.usage, "completion_tokens_details"):
                    details = response.usage.completion_tokens_details
                    if (
                        hasattr(details, "reasoning_tokens")
                        and details.reasoning_tokens
                    ):
                        logger.info(
                            f"GPT-5 reasoning tokens: {details.reasoning_tokens}"
                        )

            # Return the raw text content
            content = response.choices[0].message.content
            logger.success(
                f"Received response: {content[:100]}..."
                if len(content) > 100
                else f"Received response: {content}"
            )
            return content

        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise


# Create a StructuredLLM-compatible wrapper
@injected(protocol=AStructuredLlmOpenaiProtocol)
async def a_structured_llm_openai(  # noqa: PINJ045
    a_sllm_openai: ASllmOpenaiProtocol,
    logger: LoggerProtocol,
    /,
    text: str,
    images: list[PIL.Image.Image] | None = None,
    response_format: type[BaseModel] | None = None,
    model: str = "gpt-4o",
    **kwargs,
) -> Any:
    """
    StructuredLLM protocol implementation for direct OpenAI.

    This wraps a_sllm_openai to match the StructuredLLM protocol signature.
    """
    return await a_sllm_openai(
        text=text,
        model=model,
        images=images,
        response_format=response_format,
        **kwargs,
    )


# Instance for GPT-4o
@instance
def a_sllm_gpt4o_direct() -> "StructuredLLM":
    """Direct OpenAI GPT-4o instance."""
    from pinjected import Injected

    return Injected.partial(a_structured_llm_openai, model="gpt-4o")


# Instance for GPT-5-nano
@instance
def a_sllm_gpt5_nano_direct() -> "StructuredLLM":
    """Direct OpenAI GPT-5-nano instance."""
    from pinjected import Injected

    return Injected.partial(a_structured_llm_openai, model="gpt-5-nano")


# Instance for GPT-5
@instance
def a_sllm_gpt5_direct() -> "StructuredLLM":
    """Direct OpenAI GPT-5 instance."""
    from pinjected import Injected

    return Injected.partial(a_structured_llm_openai, model="gpt-5")


# Export design for dependency injection
__design__ = design()
