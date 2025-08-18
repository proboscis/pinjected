from typing import overload, Literal
from pinjected import IProxy
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion
from PIL.Image import Image

# IMPORTANT: @injected functions MUST use @overload in .pyi files
# The @overload decorator is required to properly type-hint the user-facing interface
# This allows IDEs to show only runtime arguments (after /) to users
# DO NOT change @overload to @injected - this is intentional for IDE support

@overload
async def a_openai_compatible_llm(
    api: AsyncOpenAI,
    model: str,
    text: str,
    images: list[Image] | None = ...,
    response_format=...,
    max_completion_tokens: int | None = ...,
    reasoning_effort=...,
    detail: Literal["auto", "low", "high"] = ...,
) -> IProxy[ChatCompletion]: ...

# Additional symbols:
class AOpenaiCompatibleLlmProtocol: ...
