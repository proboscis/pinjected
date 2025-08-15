"""Simplified refactored OpenRouter implementation following SOLID principles."""

from __future__ import annotations

import base64
import json
from io import BytesIO
from typing import Any, Protocol
from pprint import pformat

import httpx
import PIL.Image
from pydantic import BaseModel
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

from pinjected import injected


# ============================================================================
# Exceptions
# ============================================================================


class OpenRouterError(Exception):
    """Base exception for OpenRouter errors."""

    pass


class OpenRouterRateLimitError(OpenRouterError):
    """Rate limit error from OpenRouter API."""

    pass


class OpenRouterTimeOutError(OpenRouterError):
    """Timeout error from OpenRouter API."""

    pass


class OpenRouterOverloadedError(OpenRouterError):
    """Overloaded error from OpenRouter API."""

    pass


class OpenRouterTransientError(OpenRouterError):
    """Transient error that should be retried."""

    pass


# ============================================================================
# Protocols
# ============================================================================


class LoggerProtocol(Protocol):
    """Protocol for logger interface."""

    def info(self, message: str) -> None: ...
    def warning(self, message: str) -> None: ...


class ModelTableProtocol(Protocol):
    """Protocol for model table interface."""

    def supports_json_output(self, model_id: str) -> bool: ...


# ============================================================================
# Core Functions
# ============================================================================


class AOpenrouterApiCallProtocol(Protocol):
    """Protocol for OpenRouter API call function."""

    async def __call__(self, payload: dict) -> dict: ...


@injected(protocol=AOpenrouterApiCallProtocol)
async def a_openrouter_api_call(
    openrouter_api_key: str,
    openrouter_timeout_sec: float,
    logger: LoggerProtocol,
    /,
    payload: dict,
) -> dict:
    """Make a raw API call to OpenRouter with retry logic.

    Includes retry logic for transient errors but does not handle
    application-level errors (those are handled by the error handler).
    """
    # Create retry decorator for HTTP/network errors
    retry_decorator = retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=2, max=60),
        retry=retry_if_exception_type(
            (
                httpx.TimeoutException,
                httpx.NetworkError,
                httpx.ConnectError,
            )
        ),
        before_sleep=before_sleep_log(logger, "INFO"),
        reraise=True,
    )

    @retry_decorator
    async def _make_http_call() -> dict:
        async with httpx.AsyncClient() as client:
            headers = {
                "Authorization": f"Bearer {openrouter_api_key}",
                "Content-Type": "application/json",
            }

            model_name = payload.get("model")
            logger.info(f"Making API call to OpenRouter with model: {model_name}")

            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=openrouter_timeout_sec,
            )

            return response.json()

    return await _make_http_call()


class HandleOpenrouterErrorProtocol(Protocol):
    """Protocol for error handler function."""

    def __call__(self, response: dict) -> None: ...


@injected(protocol=HandleOpenrouterErrorProtocol)
def handle_openrouter_error(
    logger: LoggerProtocol,
    /,
    response: dict,
) -> None:
    """Check and handle errors in OpenRouter response.

    Raises specific exceptions based on error type.
    Does nothing if no error is present.
    """
    if "error" not in response:
        return

    error = response.get("error", {})
    error_code = error.get("code")
    error_msg = str(response)

    # Rate limit errors
    if error_code == 429 or "Rate limit" in error_msg or "rate-limited" in error_msg:
        logger.warning(f"Rate limit error: {pformat(response)}")
        raise OpenRouterRateLimitError(response)

    # Timeout errors
    if "Timed out" in error_msg:
        logger.warning(f"Timeout error: {pformat(response)}")
        raise OpenRouterTimeOutError(response)

    # Overloaded errors
    if "Overloaded" in error_msg or error_code == 502:
        logger.warning(f"Overloaded error: {pformat(response)}")
        raise OpenRouterOverloadedError(response)

    # Transient errors that should be retried
    # 520: Web server is returning an unknown error (CloudFlare)
    # 503: Service temporarily unavailable
    # 522: Connection timed out
    # 524: A timeout occurred
    transient_codes = {520, 503, 522, 524}
    if error_code in transient_codes:
        logger.warning(f"Transient error (code {error_code}): {pformat(response)}")
        raise OpenRouterTransientError(response)

    # Provider errors that might be transient
    if error_code == 520 and "Provider returned error" in error_msg:
        logger.warning(f"Provider transient error: {pformat(response)}")
        raise OpenRouterTransientError(response)

    # Generic error
    raise OpenRouterError(f"API Error: {pformat(response)}")


class AProcessImageForApiProtocol(Protocol):
    """Protocol for image processing function."""

    async def __call__(self, image: PIL.Image.Image) -> str: ...


@injected(protocol=AProcessImageForApiProtocol)
async def a_process_image_for_api(
    logger: LoggerProtocol,
    /,
    image: PIL.Image.Image,
) -> str:
    """Process a single image for API submission.

    Returns base64 encoded string of the image.
    Ensures image is under 5MB and in JPEG format.
    """
    # Convert RGBA to RGB if needed
    if image.mode == "RGBA":
        image = image.convert("RGB")

    # Try different quality levels to get under 5MB
    for quality in [95, 85, 75, 65, 50]:
        buffer = BytesIO()
        image.save(buffer, format="JPEG", quality=quality)
        size_mb = buffer.tell() / (1024 * 1024)

        if size_mb < 5:
            logger.info(f"Image processed at quality {quality}, size: {size_mb:.2f}MB")
            buffer.seek(0)
            return base64.b64encode(buffer.read()).decode("utf-8")

    # If still too large, resize
    width, height = image.size
    while True:
        width = int(width * 0.9)
        height = int(height * 0.9)
        resized = image.resize((width, height), PIL.Image.Resampling.LANCZOS)

        buffer = BytesIO()
        resized.save(buffer, format="JPEG", quality=75)
        size_mb = buffer.tell() / (1024 * 1024)

        if size_mb < 5:
            logger.info(f"Image resized to {width}x{height}, size: {size_mb:.2f}MB")
            buffer.seek(0)
            return base64.b64encode(buffer.read()).decode("utf-8")


class ABuildMessageContentProtocol(Protocol):
    """Protocol for message content builder function."""

    async def __call__(
        self, prompt: str, images: list[PIL.Image.Image] | None = None
    ) -> list[dict]: ...


@injected(protocol=ABuildMessageContentProtocol)
async def a_build_message_content(
    a_process_image_for_api: AProcessImageForApiProtocol,
    /,
    prompt: str,
    images: list[PIL.Image.Image] | None = None,
) -> list[dict]:
    """Build message content from prompt and optional images.

    Returns list of content items for OpenRouter message format.
    """
    content = [{"type": "text", "text": prompt}]

    if images:
        for image in images:
            base64_image = await a_process_image_for_api(image)
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                }
            )

    return content


class FormatResponseForJsonProtocol(Protocol):
    """Protocol for response format function."""

    def __call__(self, response_format: type[BaseModel], model: str) -> dict | None: ...


@injected(protocol=FormatResponseForJsonProtocol)
def format_response_for_json(  # noqa: PINJ045
    model_table: ModelTableProtocol,
    /,
    response_format: type[BaseModel],
    model: str,
) -> dict | None:
    """Format response schema for models that support JSON output.

    Returns OpenRouter response format dict or None if not supported.
    """
    if not model_table.supports_json_output(model):
        return None

    schema = response_format.model_json_schema()

    # Convert $defs to definitions for OpenRouter
    if "$defs" in schema:
        schema["definitions"] = schema.pop("$defs")

    return {
        "type": "json_schema",
        "json_schema": {"name": "response", "strict": False, "schema": schema},
    }


class AParseJsonResponseProtocol(Protocol):
    """Protocol for JSON response parser function."""

    async def __call__(self, content: str, response_format: type[BaseModel]) -> Any: ...


@injected(protocol=AParseJsonResponseProtocol)
async def a_parse_json_response(  # noqa: PINJ045
    logger: LoggerProtocol,
    /,
    content: str,
    response_format: type[BaseModel],
) -> Any:
    """Parse JSON response into Pydantic model.

    Simple parsing without fallback - caller handles errors.
    """
    try:
        json_data = json.loads(content)
        return response_format.model_validate(json_data)
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning(f"Failed to parse JSON response: {e}")
        # Try to extract JSON from the content
        # Look for JSON between ```json and ``` markers
        if "```json" in content:
            start = content.find("```json") + 7
            end = content.find("```", start)
            if end > start:
                try:
                    json_str = content[start:end].strip()
                    json_data = json.loads(json_str)
                    return response_format.model_validate(json_data)
                except Exception:
                    pass
        raise


# ============================================================================
# Main Refactored Function
# ============================================================================


class ARefactoredChatCompletionProtocol(Protocol):
    """Protocol for main refactored chat completion function."""

    async def __call__(
        self,
        prompt: str,
        model: str = "openai/gpt-4o-mini",
        max_tokens: int = 8192,
        temperature: float = 1.0,
        images: list[PIL.Image.Image] | None = None,
        response_format: type[BaseModel] | None = None,
        **kwargs,
    ) -> dict[str, Any]: ...


@injected(protocol=ARefactoredChatCompletionProtocol)
async def a_refactored_chat_completion(  # noqa: PINJ045
    a_openrouter_api_call: AOpenrouterApiCallProtocol,
    handle_openrouter_error: HandleOpenrouterErrorProtocol,
    a_build_message_content: ABuildMessageContentProtocol,
    format_response_for_json: FormatResponseForJsonProtocol,
    a_parse_json_response: AParseJsonResponseProtocol,
    logger: LoggerProtocol,
    model_table: ModelTableProtocol,
    /,
    prompt: str,
    model: str = "openai/gpt-4o-mini",
    max_tokens: int = 8192,
    temperature: float = 1.0,
    images: list[PIL.Image.Image] | None = None,
    response_format: type[BaseModel] | None = None,
    **kwargs,
) -> dict[str, Any]:
    """Refactored OpenRouter chat completion.

    This is a simplified refactored version that:
    - Separates concerns into focused functions
    - Uses dependency injection for all components
    - Keeps the interface simple and clean
    - Avoids over-engineering

    Returns:
        Dictionary with "result" key containing the response
    """
    # Build message content
    content = await a_build_message_content(prompt, images)

    # Build base payload
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": content}],
        "max_tokens": max_tokens,
        "temperature": temperature,
        **kwargs,
    }

    # Add response format if provided and supported
    if response_format:
        json_format = format_response_for_json(response_format, model)
        if json_format:
            payload["response_format"] = json_format
            # Ensure provider supports parameters
            if "provider" not in payload:
                payload["provider"] = {}
            payload["provider"]["require_parameters"] = True
        else:
            # Add instruction to prompt for models that don't support JSON mode
            content[0]["text"] += (
                f"\n\nRespond with valid JSON matching this schema:\n{response_format.model_json_schema()}"
            )

    # Make API call (network retries are handled in a_openrouter_api_call)
    response = await a_openrouter_api_call(payload)

    # Check for application-level errors and raise appropriate exceptions
    # These exceptions can be caught by retry logic at higher levels
    handle_openrouter_error(response)

    # Extract content from response
    message_content = response["choices"][0]["message"]["content"]

    # Parse structured response if needed
    if response_format:
        try:
            result = await a_parse_json_response(message_content, response_format)
        except Exception as e:
            logger.warning(f"Failed to parse structured response: {e}")
            # Return raw content as fallback
            result = message_content
    else:
        result = message_content

    # Log usage if available
    if "usage" in response:
        usage = response["usage"]
        logger.info(
            f"API call completed - Model: {model}, "
            f"Prompt tokens: {usage.get('prompt_tokens', 0)}, "
            f"Completion tokens: {usage.get('completion_tokens', 0)}"
        )

    return {"result": result}


# ============================================================================
# Convenience Wrappers
# ============================================================================


class ASimpleCompletionProtocol(Protocol):
    """Protocol for simple completion function."""

    async def __call__(
        self, prompt: str, model: str = "openai/gpt-4o-mini", **kwargs
    ) -> str: ...


@injected(protocol=ASimpleCompletionProtocol)
async def a_simple_completion(
    a_refactored_chat_completion: ARefactoredChatCompletionProtocol,
    /,
    prompt: str,
    model: str = "openai/gpt-4o-mini",
    **kwargs,
) -> str:
    """Simple text completion without structured output."""
    response = await a_refactored_chat_completion(
        prompt=prompt,
        model=model,
        **kwargs,
    )
    return response["result"]


class AJsonCompletionProtocol(Protocol):
    """Protocol for JSON completion function."""

    async def __call__(
        self,
        prompt: str,
        response_model: type[BaseModel],
        model: str = "openai/gpt-4o-mini",
        **kwargs,
    ) -> BaseModel: ...


@injected(protocol=AJsonCompletionProtocol)
async def a_json_completion(
    a_refactored_chat_completion: ARefactoredChatCompletionProtocol,
    /,
    prompt: str,
    response_model: type[BaseModel],
    model: str = "openai/gpt-4o-mini",
    **kwargs,
) -> BaseModel:
    """Completion with structured JSON output."""
    response = await a_refactored_chat_completion(
        prompt=prompt,
        model=model,
        response_format=response_model,
        **kwargs,
    )
    return response["result"]


class AVisionCompletionProtocol(Protocol):
    """Protocol for vision completion function."""

    async def __call__(
        self,
        prompt: str,
        images: list[PIL.Image.Image],
        model: str = "openai/gpt-4o-mini",
        **kwargs,
    ) -> str: ...


@injected(protocol=AVisionCompletionProtocol)
async def a_vision_completion(
    a_refactored_chat_completion: ARefactoredChatCompletionProtocol,
    /,
    prompt: str,
    images: list[PIL.Image.Image],
    model: str = "openai/gpt-4o-mini",
    **kwargs,
) -> str:
    """Completion with image inputs."""
    response = await a_refactored_chat_completion(
        prompt=prompt,
        model=model,
        images=images,
        **kwargs,
    )
    return response["result"]
