"""Stub file for direct OpenAI API implementation."""

from typing import Any, Protocol, overload
import PIL.Image
from pinjected import IProxy
from pinjected_openai.openrouter.instances import StructuredLLM
from pydantic import BaseModel

class LoggerProtocol(Protocol):
    def debug(self, message: str) -> None: ...
    def info(self, message: str) -> None: ...
    def warning(self, message: str) -> None: ...
    def error(self, message: str) -> None: ...
    def success(self, message: str) -> None: ...

class ASllmOpenaiProtocol(Protocol):
    async def __call__(
        self,
        text: str,
        model: str = ...,
        images: list[PIL.Image.Image] | None = ...,
        response_format: type[BaseModel] | None = ...,
        max_tokens: int = ...,
        temperature: float = ...,
        reasoning_effort: str | None = ...,
        verbosity: str | None = ...,
        **kwargs,
    ) -> Any: ...

class AStructuredLlmOpenaiProtocol(Protocol):
    async def __call__(
        self,
        text: str,
        images: list[PIL.Image.Image] | None = ...,
        response_format: type[BaseModel] | None = ...,
        model: str = ...,
        **kwargs,
    ) -> Any: ...

def is_gpt5_model(model: str) -> bool: ...
def requires_max_completion_tokens(model: str) -> bool: ...
def convert_pil_to_base64(image: PIL.Image.Image) -> str: ...
def ensure_strict_schema(schema: dict) -> dict: ...

# Injected function signatures with @overload as required by linter
@overload
async def a_sllm_openai(
    text: str,
    model: str = ...,
    images: list[PIL.Image.Image] | None = ...,
    response_format: type[BaseModel] | None = ...,
    max_tokens: int = ...,
    temperature: float = ...,
    reasoning_effort: str | None = ...,
    verbosity: str | None = ...,
    **kwargs,
) -> IProxy[Any]: ...
@overload
async def a_structured_llm_openai(
    text: str,
    images: list[PIL.Image.Image] | None = ...,
    response_format: type[BaseModel] | None = ...,
    model: str = ...,
    **kwargs,
) -> IProxy[Any]: ...

# IProxy variable declarations
a_sllm_openai: IProxy[ASllmOpenaiProtocol]
a_structured_llm_openai: IProxy[AStructuredLlmOpenaiProtocol]

# Instance IProxy declarations
a_sllm_gpt4o_direct: IProxy[StructuredLLM]
a_sllm_gpt5_nano_direct: IProxy[StructuredLLM]
a_sllm_gpt5_direct: IProxy[StructuredLLM]

# Design export
__design__: Any
