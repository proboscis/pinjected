from pinjected import *
from pydantic import BaseModel

from pinjected_openai.vision_llm import to_content
from openai.types.chat import ChatCompletion
from openai import AsyncOpenAI
from typing import Optional,Literal
from PIL.Image import Image
@injected
async def a_openai_compatible_llm(
        logger,
        /,
        api:AsyncOpenAI,
        model:str,
        text:str,
        images:Optional[list[Image]]=None,
        response_format=None,
        max_completion_tokens:int = None,
        reasoning_effort=None,
        detail:Literal["auto","low","high"] = "auto"
)->ChatCompletion:
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
        api_kwargs['max_completion_tokens'] = max_completion_tokens
    if reasoning_effort is not None:
        api_kwargs['reasoning_effort'] = reasoning_effort
    if isinstance(response_format,type) and issubclass(response_format,BaseModel):
        api_kwargs['response_format'] = response_format.model_json_schema()
        api_object = api.beta.chat.completions.parse
    else:
        api_object = api.chat.completions.create

    return await api_object(**api_kwargs)

