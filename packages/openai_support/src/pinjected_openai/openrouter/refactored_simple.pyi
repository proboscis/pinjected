"""Type stubs for refactored_simple module."""

from typing import Any, Protocol, overload
from pydantic import BaseModel
import PIL.Image

# ============================================================================
# Protocols for @injected functions
# ============================================================================

class AOpenrouterApiCallProtocol(Protocol):
    """Protocol for OpenRouter API call function."""
    async def __call__(self, payload: dict) -> dict: ...

class HandleOpenrouterErrorProtocol(Protocol):
    """Protocol for error handler function."""
    def __call__(self, response: dict) -> None: ...

class AProcessImageForApiProtocol(Protocol):
    """Protocol for image processing function."""
    async def __call__(self, image: PIL.Image.Image) -> str: ...

class ABuildMessageContentProtocol(Protocol):
    """Protocol for message content builder function."""
    async def __call__(
        self, prompt: str, images: list[PIL.Image.Image] | None = None
    ) -> list[dict]: ...

class FormatResponseForJsonProtocol(Protocol):
    """Protocol for response format function."""
    def __call__(self, response_format: type[BaseModel], model: str) -> dict | None: ...

class AParseJsonResponseProtocol(Protocol):
    """Protocol for JSON response parser function."""
    async def __call__(self, content: str, response_format: type[BaseModel]) -> Any: ...

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

class ASimpleCompletionProtocol(Protocol):
    """Protocol for simple completion function."""
    async def __call__(
        self, prompt: str, model: str = "openai/gpt-4o-mini", **kwargs
    ) -> str: ...

class AJsonCompletionProtocol(Protocol):
    """Protocol for JSON completion function."""
    async def __call__(
        self,
        prompt: str,
        response_model: type[BaseModel],
        model: str = "openai/gpt-4o-mini",
        **kwargs,
    ) -> BaseModel: ...

class AVisionCompletionProtocol(Protocol):
    """Protocol for vision completion function."""
    async def __call__(
        self,
        prompt: str,
        images: list[PIL.Image.Image],
        model: str = "openai/gpt-4o-mini",
        **kwargs,
    ) -> str: ...

# ============================================================================
# Function overloads for IDE support
# ============================================================================

@overload
async def a_openrouter_api_call(payload: dict) -> dict: ...
@overload
def handle_openrouter_error(response: dict) -> None: ...
@overload
async def a_process_image_for_api(image: PIL.Image.Image) -> str: ...
@overload
async def a_build_message_content(
    prompt: str, images: list[PIL.Image.Image] | None = None
) -> list[dict]: ...
@overload
def format_response_for_json(
    response_format: type[BaseModel], model: str
) -> dict | None: ...
@overload
async def a_parse_json_response(
    content: str, response_format: type[BaseModel]
) -> Any: ...
@overload
async def a_refactored_chat_completion(
    prompt: str,
    model: str = "openai/gpt-4o-mini",
    max_tokens: int = 8192,
    temperature: float = 1.0,
    images: list[PIL.Image.Image] | None = None,
    response_format: type[BaseModel] | None = None,
    **kwargs,
) -> dict[str, Any]: ...
@overload
async def a_simple_completion(
    prompt: str, model: str = "openai/gpt-4o-mini", **kwargs
) -> str: ...
@overload
async def a_json_completion(
    prompt: str,
    response_model: type[BaseModel],
    model: str = "openai/gpt-4o-mini",
    **kwargs,
) -> BaseModel: ...
@overload
async def a_vision_completion(
    prompt: str,
    images: list[PIL.Image.Image],
    model: str = "openai/gpt-4o-mini",
    **kwargs,
) -> str: ...

# ============================================================================
# Exception classes
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
# Protocol definitions
# ============================================================================

class LoggerProtocol(Protocol):
    """Protocol for logger interface."""
    def info(self, message: str) -> None: ...
    def warning(self, message: str) -> None: ...

class ModelTableProtocol(Protocol):
    """Protocol for model table interface."""
    def supports_json_output(self, model_id: str) -> bool: ...
