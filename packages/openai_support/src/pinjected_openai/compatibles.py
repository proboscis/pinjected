from typing import Literal, Any, Protocol

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion
from PIL.Image import Image
from pinjected_openai.vision_llm import to_content
from pydantic import BaseModel

from pinjected import *


class AOpenaiCompatibleLlmProtocol(Protocol):
    async def __call__(
        self,
        api: AsyncOpenAI,
        model: str,
        text: str,
        images: list[Image] | None = None,
        response_format=None,
        max_completion_tokens: int | None = None,
        reasoning_effort=None,
        detail: Literal["auto", "low", "high"] = "auto",
    ) -> ChatCompletion: ...


@injected(protocol=AOpenaiCompatibleLlmProtocol)
async def a_openai_compatible_llm(  # noqa: PINJ045
    logger: Any,
    /,
    api: AsyncOpenAI,
    model: str,
    text: str,
    images: list[Image] | None = None,
    response_format=None,
    max_completion_tokens: int | None = None,
    reasoning_effort=None,
    detail: Literal["auto", "low", "high"] = "auto",
) -> ChatCompletion:
    images = images or []

    api_kwargs = dict(
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": text},
                    *[to_content(img, detail=detail) for img in images],
                ],
            }
        ],
        model=model,
        response_format=response_format,
    )

    if max_completion_tokens is not None:
        api_kwargs["max_completion_tokens"] = max_completion_tokens
    if reasoning_effort is not None:
        api_kwargs["reasoning_effort"] = reasoning_effort
    if isinstance(response_format, type) and issubclass(response_format, BaseModel):
        api_kwargs["response_format"] = response_format.model_json_schema()
        api_object = api.beta.chat.completions.parse
    else:
        api_object = api.chat.completions.create

    return await api_object(**api_kwargs)
