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

from pinjected_openai.openai_pricing import (
    OpenAIModelTable,
    log_completion_cost,
)

if TYPE_CHECKING:
    from pinjected_openai.openrouter.instances import StructuredLLM


class LoggerProtocol(Protocol):
    def debug(self, message: str) -> None: ...
    def info(self, message: str) -> None: ...
    def warning(self, message: str) -> None: ...
    def error(self, message: str) -> None: ...
    def success(self, message: str) -> None: ...


class ASllmOpenaiProtocol(Protocol):
    """Protocol for direct OpenAI structured LLM with GPT-5 thinking mode support."""

    async def __call__(
        self,
        text: str,
        model: str = "gpt-4o",
        images: list[PIL.Image.Image] | None = None,
        response_format: type[BaseModel] | None = None,
        max_tokens: int = 8192,
        temperature: float = 0.7,
        reasoning_effort: str | None = None,
        verbosity: str | None = None,
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


def requires_max_completion_tokens(model: str) -> bool:
    """Check if model requires max_completion_tokens instead of max_tokens."""
    model_lower = model.lower()
    # GPT-5 and o1/o3/o4 models require max_completion_tokens
    return (
        "gpt-5" in model_lower
        or "gpt5" in model_lower
        or model_lower.startswith("o1")
        or model_lower.startswith("o3")
        or model_lower.startswith("o4")
    )


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


def ensure_strict_schema(schema: dict) -> dict:
    """
    Recursively ensure all objects in schema have additionalProperties: false.
    This is required for OpenAI's strict mode.
    """
    if not isinstance(schema, dict):
        return schema

    # Create a copy to avoid mutation
    result = dict(schema)

    # Set additionalProperties: false for this object
    if "type" in result and result["type"] == "object":
        result["additionalProperties"] = False

    # Process nested schemas in properties
    if "properties" in result:
        new_properties = {}
        for prop_name, prop_schema in result["properties"].items():
            new_properties[prop_name] = ensure_strict_schema(prop_schema)
        result["properties"] = new_properties

    # Process items in arrays
    if "items" in result:
        result["items"] = ensure_strict_schema(result["items"])

    # Process nested definitions/defs
    if "definitions" in result:
        new_definitions = {}
        for def_name, def_schema in result["definitions"].items():
            new_definitions[def_name] = ensure_strict_schema(def_schema)
        result["definitions"] = new_definitions

    if "$defs" in result:
        new_defs = {}
        for def_name, def_schema in result["$defs"].items():
            new_defs[def_name] = ensure_strict_schema(def_schema)
        result["$defs"] = new_defs

    return result


def _build_messages(
    text: str, images: list[PIL.Image.Image] | None = None, **kwargs
) -> list[dict]:
    """
    Build the messages array for OpenAI API call.

    Args:
        text: The prompt text
        images: Optional list of PIL images to include
        **kwargs: Additional parameters (detail level for images)

    Returns:
        List of message dictionaries for the API call
    """
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

    return messages


def _build_api_parameters(
    model: str,
    messages: list[dict],
    temperature: float,
    max_tokens: int,
    reasoning_effort: str | None,
    verbosity: str | None,
    response_format: type[BaseModel] | None,
    logger: LoggerProtocol,
    **kwargs,
) -> dict:
    """
    Build API parameters for OpenAI API call with model-specific handling.

    Args:
        model: OpenAI model name
        messages: List of message dictionaries
        temperature: Temperature for sampling
        max_tokens: Maximum tokens for completion
        reasoning_effort: GPT-5 thinking mode control
        verbosity: GPT-5 output detail control
        response_format: Optional Pydantic BaseModel for structured output
        logger: Logger instance for output
        **kwargs: Additional API parameters

    Returns:
        Dictionary of API parameters ready for OpenAI API call
    """
    # Build the API call parameters
    api_params = {
        "model": model,
        "messages": messages,
        **kwargs,  # Pass through any additional parameters
    }

    # Apply model-specific parameters using the handler class
    ModelParameterHandler.apply_model_specific_params(
        api_params, model, temperature, max_tokens, reasoning_effort, verbosity, logger
    )

    # Handle structured output if requested
    if response_format is not None and issubclass(response_format, BaseModel):
        logger.debug(f"Using structured output with {response_format.__name__}")

        # Get the JSON schema and ensure it's properly formatted for OpenAI
        schema = response_format.model_json_schema()
        # Recursively ensure all objects have additionalProperties: false for strict mode
        schema = ensure_strict_schema(schema)
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

    return api_params


def _log_usage_and_cost(
    response,
    model: str,
    openai_model_table,
    openai_state: dict,
    logger: LoggerProtocol,
) -> None:
    """
    Log token usage information and calculate costs.

    Args:
        response: OpenAI API response object
        model: Model name used for the request
        openai_model_table: Model pricing table
        openai_state: Current state dictionary for tracking
        logger: Logger instance for output
    """
    if not response.usage:
        return

    logger.info(f"Token usage: {response.usage.model_dump()}")

    if hasattr(response.usage, "completion_tokens_details"):
        details = response.usage.completion_tokens_details
        if hasattr(details, "reasoning_tokens") and details.reasoning_tokens:
            logger.info(f"GPT-5 reasoning tokens: {details.reasoning_tokens}")

    # Calculate and log cost
    usage_dict = response.usage.model_dump()
    # Create new state with incremented request count
    current_state = {
        **openai_state,
        "request_count": openai_state.get("request_count", 0) + 1,
    }
    log_completion_cost(usage_dict, model, openai_model_table, current_state, logger)


def _process_structured_response(
    response, response_format: type[BaseModel], logger: LoggerProtocol
) -> Any:
    """
    Process structured response from OpenAI API.

    Args:
        response: OpenAI API response object
        response_format: Pydantic BaseModel for structured output
        logger: Logger instance for output

    Returns:
        Parsed response according to response_format

    Raises:
        json.JSONDecodeError: If response content is not valid JSON
        ValidationError: If response doesn't match the expected format
    """
    # Extract the content
    content = response.choices[0].message.content

    # Parse the JSON response
    try:
        parsed_json = json.loads(content)
        result = response_format(**parsed_json)
        logger.success(f"Successfully parsed response as {response_format.__name__}")
        return result
    except (json.JSONDecodeError, ValidationError) as e:
        logger.error(f"Failed to parse structured response: {e}")
        logger.debug(f"Raw content: {content}")
        raise


def _process_unstructured_response(response, logger: LoggerProtocol) -> str:
    """
    Process unstructured text response from OpenAI API.

    Args:
        response: OpenAI API response object
        logger: Logger instance for output

    Returns:
        Raw text content from the response
    """
    # Return the raw text content
    content = response.choices[0].message.content
    logger.success(
        f"Received response: {content[:100]}..."
        if len(content) > 100
        else f"Received response: {content}"
    )
    return content


class ModelParameterHandler:
    """
    Handles model-specific parameter configuration for OpenAI API calls.

    Encapsulates the logic for different model types (GPT-5, o1/o3/o4 vs others)
    and their specific parameter requirements.
    """

    @staticmethod
    def apply_model_specific_params(
        api_params: dict,
        model: str,
        temperature: float,
        max_tokens: int,
        reasoning_effort: str | None,
        verbosity: str | None,
        logger: LoggerProtocol,
    ) -> None:
        """
        Apply model-specific parameters to the API parameters dictionary.

        Args:
            api_params: Dictionary of API parameters to modify
            model: OpenAI model name
            temperature: Temperature for sampling
            max_tokens: Maximum tokens for completion
            reasoning_effort: GPT-5 thinking mode control
            verbosity: GPT-5 output detail control
            logger: Logger instance for output
        """
        # GPT-5 and o1/o3/o4 models only support temperature=1.0
        model_lower = model.lower()
        if (
            is_gpt5_model(model)
            or model_lower.startswith("o1")
            or model_lower.startswith("o3")
            or model_lower.startswith("o4")
        ):
            # These models only support default temperature (1.0)
            if temperature != 1.0:
                logger.debug(
                    f"{model} only supports temperature=1.0, ignoring temperature={temperature}"
                )
        else:
            # Other models support custom temperature
            api_params["temperature"] = temperature

        # Handle token parameter based on model
        if requires_max_completion_tokens(model):
            # GPT-5, o1, o3, o4 models require max_completion_tokens
            # Ensure sufficient tokens for reasoning + output
            token_value = max(max_tokens, 500)  # Minimum 500 for these models
            api_params["max_completion_tokens"] = token_value
            logger.debug(f"Using max_completion_tokens={token_value} for model {model}")

            # Add GPT-5 thinking mode parameters
            if reasoning_effort:
                valid_efforts = ["minimal", "low", "medium", "high"]
                if reasoning_effort not in valid_efforts:
                    logger.warning(
                        f"Invalid reasoning_effort '{reasoning_effort}'. "
                        f"Valid options: {valid_efforts}"
                    )
                else:
                    api_params["reasoning_effort"] = reasoning_effort
                    logger.info(
                        f"Using reasoning_effort='{reasoning_effort}' for thinking mode. "
                        f"{'Minimal reasoning for fast response.' if reasoning_effort == 'minimal' else ''}"
                        f"{'Light reasoning for moderate complexity.' if reasoning_effort == 'low' else ''}"
                        f"{'Balanced reasoning for most cases.' if reasoning_effort == 'medium' else ''}"
                        f"{'Deep reasoning for complex problems.' if reasoning_effort == 'high' else ''}"
                    )

            if verbosity:
                valid_verbosity = ["low", "medium", "high"]
                if verbosity not in valid_verbosity:
                    logger.warning(
                        f"Invalid verbosity '{verbosity}'. Valid options: {valid_verbosity}"
                    )
                else:
                    api_params["verbosity"] = verbosity
                    logger.debug(
                        f"Using verbosity='{verbosity}' for output detail control"
                    )
        else:
            # Other models use max_tokens
            api_params["max_tokens"] = max_tokens
            logger.debug(f"Using max_tokens={max_tokens} for model {model}")

            # Warn if GPT-5 specific parameters are used with non-GPT-5 models
            if reasoning_effort:
                logger.warning(
                    f"reasoning_effort parameter is only supported for GPT-5 models, "
                    f"ignoring for {model}"
                )
            if verbosity:
                logger.warning(
                    f"verbosity parameter is only supported for GPT-5 models, "
                    f"ignoring for {model}"
                )


@injected(protocol=ASllmOpenaiProtocol)
async def a_sllm_openai(  # noqa: PINJ045
    async_openai_client: AsyncOpenAI,
    logger: LoggerProtocol,
    openai_model_table: OpenAIModelTable,
    openai_state: dict,
    /,
    text: str,
    model: str = "gpt-4o",
    images: list[PIL.Image.Image] | None = None,
    response_format: type[BaseModel] | None = None,
    max_tokens: int = 8192,
    temperature: float = 0.7,
    reasoning_effort: str | None = None,
    verbosity: str | None = None,
    **kwargs,
) -> Any:
    """
    Direct OpenAI API structured LLM implementation with GPT-5 thinking mode support.

    This function bypasses OpenRouter and calls OpenAI directly, avoiding the 5% fee.
    It properly handles GPT-5 models including their advanced thinking mode capabilities.

    Args:
        text: The prompt text
        model: OpenAI model name (e.g., "gpt-4o", "gpt-5-nano", "gpt-5")
        images: Optional list of PIL images to include
        response_format: Optional Pydantic BaseModel for structured output
        max_tokens: Maximum tokens for completion (transformed to max_completion_tokens for GPT-5)
        temperature: Temperature for sampling (GPT-5 only supports 1.0)
        reasoning_effort: GPT-5 thinking mode control. Options:
            - "minimal": Few/no reasoning tokens, fastest response for simple tasks
            - "low": Light reasoning for moderately complex tasks
            - "medium": Balanced reasoning for most use cases (default for complex prompts)
            - "high": Deep reasoning for complex problems requiring extensive thinking
            Note: Higher effort = more reasoning tokens = higher cost but better quality
        verbosity: GPT-5 output detail control. Options:
            - "low": Concise responses
            - "medium": Balanced detail (default)
            - "high": Detailed, comprehensive responses
        **kwargs: Additional OpenAI API parameters

    GPT-5 Thinking Mode Usage:
        For simple tasks (extraction, formatting, classification):
            reasoning_effort="minimal"  # Fastest, lowest cost

        For complex reasoning (math, analysis, planning):
            reasoning_effort="high"  # Best quality, shows thinking process

        The model automatically uses "reasoning tokens" (invisible tokens that count
        toward billing) to think through problems before generating the response.
        You can see reasoning token usage in the response.usage.completion_tokens_details.

    Returns:
        Parsed response according to response_format, or raw text if no format specified
    """
    logger.debug(
        f"a_sllm_openai called with model={model}, response_format={response_format}"
    )

    try:
        messages = _build_messages(text, images, **kwargs)

        # Phase 2: Build API parameters
        api_params = _build_api_parameters(
            model,
            messages,
            temperature,
            max_tokens,
            reasoning_effort,
            verbosity,
            response_format,
            logger,
            **kwargs,
        )

        # Phase 3: Make API call
        response = await async_openai_client.chat.completions.create(**api_params)

        _log_usage_and_cost(response, model, openai_model_table, openai_state, logger)

        if response_format is not None and issubclass(response_format, BaseModel):
            return _process_structured_response(response, response_format, logger)
        else:
            return _process_unstructured_response(response, logger)

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
