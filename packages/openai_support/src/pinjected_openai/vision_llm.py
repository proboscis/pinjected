import asyncio
import base64
import io
import json
import random
import re
from asyncio import Lock
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Literal, Callable, Optional, Awaitable

import openai.types.chat
import pandas as pd
import reactivex
from PIL.Image import Image
from injected_utils.injected_cache_utils import async_cached, sqlite_dict
from loguru import logger
from math import ceil
from openai import AsyncOpenAI, RateLimitError, APITimeoutError, APIConnectionError
from openai.types.chat import ChatCompletion
from pydantic import BaseModel
from pydantic import Field
from pinjected import *
from tenacity import retry,stop_after_attempt,retry_if_exception_type

class ChatCompletionWithCost(BaseModel):
    src: ChatCompletion
    total_cost_usd: float
    prompt_cost_usd: float
    completion_cost_usd: float


@instance
def chat_completion_costs_subject():
    return reactivex.Subject()


def to_content(img: Image, detail: Literal["auto", "low", "high"] = "auto"):
    # convert Image into jpeg bytes
    jpg_bytes = io.BytesIO()
    img.convert("RGB").save(jpg_bytes, format="jpeg", quality=95)
    b64_image = base64.b64encode(jpg_bytes.getvalue()).decode("utf-8")
    mb_of_b64 = len(b64_image) / 1024 / 1024
    logger.info(f"image size: {mb_of_b64:.2f} MB in base64.")
    return {
        "type": "image_url",
        "image_url": dict(url=f"data:image/jpeg;base64,{b64_image}", detail=detail),
    }


@dataclass
class UsageEntry:
    timestamp: datetime
    tokens: int

    class Config:
        arbitrary_types_allowed = True


class RateLimitManager(BaseModel):
    max_tokens: int
    max_calls: int
    duration: timedelta
    lock: Lock = asyncio.Lock()
    call_history: list[UsageEntry] = []

    async def acquire(self, approx_tokens):
        if await self.ready(approx_tokens):
            pass
        else:
            # wait for some time or condition, but who checks the condition?
            # a distinct loop, or loop here?
            # 1. check if we need to wait
            # 2. check if someone else is waiting with loop
            # 3. if not use looping to wait
            # Currently, everyone waits with loops
            while not await self.ready(approx_tokens):
                await asyncio.sleep(1)

    async def ready(self, token):
        async with self.lock:
            remaining = await self.remaining_tokens()
            is_ready = remaining >= token and len(self.call_history) < self.max_calls
            if is_ready:
                self.call_history.append(UsageEntry(pd.Timestamp.now(), token))
            return is_ready

    async def remaining_tokens(self):
        return self.max_tokens - await self._current_usage()

    async def remaining_calls(self):
        return self.max_calls - len(self.call_history)

    async def _current_usage(self):
        t = pd.Timestamp.now()
        self.call_history = [
            e for e in self.call_history if e.timestamp > t - self.duration
        ]
        return sum(e.tokens for e in self.call_history)

    class Config:
        arbitrary_types_allowed = True


class RateLimitKey(BaseModel):
    api_key: str
    organization: str
    model_name: str
    request_type: str


class BatchQueueLimits(BaseModel):
    tpm: int = Field(None, alias="TPM")
    rpm: int = Field(None, alias="RPM")
    tpd: int = Field(None, alias="TPD")
    images_per_minute: int = None


class ModelLimits(BaseModel):
    modeltoken_limits: int = None
    request_limits: int = None
    other_limits: int = None
    batch_queue_limits: BatchQueueLimits


class Limits(BaseModel):
    gpt_4: ModelLimits = Field(None, alias="gpt-4")
    gpt_3_5_turbo: ModelLimits = Field(None, alias="gpt-3.5-turbo")
    gpt_4_turbo: ModelLimits = Field(None, alias="gpt-4-turbo")
    text_embedding_3_small: ModelLimits = Field(None, alias="text-embedding-3-small")
    dall_e_3: ModelLimits = Field(None, alias="dall-e-3")
    tts_1: ModelLimits = Field(None, alias="tts-1")
    whisper_1: ModelLimits = Field(None, alias="whisper-1")


personal_limits = Limits(
    gpt_4=ModelLimits(
        modeltoken_limits=10000000,
        request_limits=10000,
        other_limits=1500000000,
        batch_queue_limits=BatchQueueLimits(tpm=300000, rpm=10000, tpd=45000000),
    ),
    gpt_3_5_turbo=ModelLimits(
        modeltoken_limits=2000000,
        request_limits=10000,
        other_limits=300000000,
        batch_queue_limits=BatchQueueLimits(tpm=2000000, rpm=10000, tpd=300000000),
    ),
    gpt_4_turbo=ModelLimits(
        modeltoken_limits=2000000,
        request_limits=10000,
        other_limits=300000000,
        batch_queue_limits=BatchQueueLimits(tpm=2000000, rpm=10000, tpd=300000000),
    ),
    text_embedding_3_small=ModelLimits(
        modeltoken_limits=10000000,
        request_limits=10000,
        other_limits=4000000000,
        batch_queue_limits=BatchQueueLimits(tpm=10000000, rpm=10000, tpd=4000000000),
    ),
    dall_e_3=ModelLimits(batch_queue_limits=BatchQueueLimits(images_per_minute=50)),
    tts_1=ModelLimits(batch_queue_limits=BatchQueueLimits(rpm=500)),
    whisper_1=ModelLimits(batch_queue_limits=BatchQueueLimits(rpm=500)),
)


class ModelPricing(BaseModel):
    input_cost: float
    output_cost: float


class PricingModel(BaseModel):
    gpt_4_turbo: ModelPricing = ModelPricing(input_cost=0.0100, output_cost=0.0300)
    gpt_4_turbo_2024_04_09: ModelPricing = ModelPricing(
        input_cost=0.0100, output_cost=0.0300
    )
    gpt_4: ModelPricing = ModelPricing(input_cost=0.0300, output_cost=0.0600)
    gpt_4_32k: ModelPricing = ModelPricing(input_cost=0.0600, output_cost=0.1200)
    gpt_4_0125_preview: ModelPricing = ModelPricing(
        input_cost=0.0100, output_cost=0.0300
    )
    gpt_4_1106_preview: ModelPricing = ModelPricing(
        input_cost=0.0100, output_cost=0.0300
    )
    gpt_4_vision_preview: ModelPricing = ModelPricing(
        input_cost=0.0100, output_cost=0.0300
    )
    gpt_3_5_turbo_1106: ModelPricing = ModelPricing(
        input_cost=0.0010, output_cost=0.0020
    )
    gpt_3_5_turbo_0613: ModelPricing = ModelPricing(
        input_cost=0.0015, output_cost=0.0020
    )
    gpt_3_5_turbo_16k_0613: ModelPricing = ModelPricing(
        input_cost=0.0030, output_cost=0.0040
    )
    gpt_3_5_turbo_0301: ModelPricing = ModelPricing(
        input_cost=0.0015, output_cost=0.0020
    )
    davinci_002: ModelPricing = ModelPricing(input_cost=0.0020, output_cost=0.0020)
    babbage_002: ModelPricing = ModelPricing(input_cost=0.0004, output_cost=0.0004)
    gpt_4o_mini_2024_07_18:ModelPricing = ModelPricing(input_cost=0.15*0.001, output_cost=0.6*0.001)
    gpt_4o: ModelPricing = ModelPricing(input_cost=0.0025, output_cost=0.0150)
    gpt_4o_2024_05_13: ModelPricing = ModelPricing(
        input_cost=0.0025, output_cost=0.0150
    )
    gpt_4o_2024_08_06: ModelPricing = ModelPricing(
        input_cost=0.0025, output_cost=0.0150
    )
    # o3_mini_2025_01_31: ModelPricing = ModelPricing(input_cost=1.10/1000, output_cost=4.40/1000)
    o3_mini_2025_01_31: ModelPricing = ModelPricing(
        input_cost=0.0011, output_cost=0.0044
    )
    o1_2024_12_17: ModelPricing = ModelPricing(input_cost=0.0151, output_cost=0.060)


pricing_model = PricingModel()


@instance
def openai_rate_limit_managers(
    openai_api_key, openai_organization, openai_rate_limits: Limits
) -> dict[Any, RateLimitManager]:
    managers = dict()
    for model, limits in openai_rate_limits.dict().items():
        key = RateLimitKey(
            api_key=openai_api_key,
            organization=openai_organization,
            model_name=model,
            request_type="completion",
        )
        managers[key] = RateLimitManager(
            max_tokens=limits.modeltoken_limits,
            max_counts=limits.request_limits,
            duration=pd.Timedelta("1 minute"),
        )
    return managers


@injected
async def a_repeat_for_rate_limit(logger, /, task):
    default_wait = 10
    while True:
        try:
            return await task()
        except RateLimitError as e:
            logger.error(f"rate limit error: {e}")
            pat = r"Please try again in (\d+) seconds."
            match = re.search(pat, e.message)
            if match:
                seconds = int(match.group(1))
                logger.info(f"sleeping for {seconds} seconds")
                await asyncio.sleep(seconds)
            else:
                logger.warning(f"failed to parse rate limit error message: {e.message}")
                zitter = random.random() * 30
                to_wait = default_wait + zitter
                await asyncio.sleep(to_wait)
                default_wait = to_wait
        except APITimeoutError as e:
            logger.warning(f"API timeout error: {e}")
            await asyncio.sleep(10)
        except APIConnectionError as ace:
            logger.warning(f"API connection error: {ace}")
            await asyncio.sleep(10)


def resize(width, height):
    if width > 1024 or height > 1024:
        if width > height:
            height = int(height * 1024 / width)
            width = 1024
        else:
            width = int(width * 1024 / height)
            height = 1024
    return width, height


@injected
def openai_count_image_tokens(width: int, height: int):
    width, height = resize(width, height)
    h = ceil(height / 512)
    w = ceil(width / 512)
    total = 85 + 170 * h * w
    return total


@injected
async def a_chat_completion_to_cost(
    openai_model_pricing_table: dict[str, ModelPricing], /, completion: ChatCompletion
) -> ChatCompletionWithCost:
    pricing = openai_model_pricing_table[completion.model]
    usage = completion.usage
    return ChatCompletionWithCost(
        src=completion,
        total_cost_usd=pricing.input_cost * usage.prompt_tokens / 1000
        + pricing.output_cost * usage.completion_tokens / 1000,
        prompt_cost_usd=pricing.input_cost * usage.prompt_tokens / 1000,
        completion_cost_usd=pricing.output_cost * usage.completion_tokens / 1000,
    )


@instance
def openai_model_pricing_table(logger):
    keys = pricing_model.dict().keys()
    # keys = [k.replace("_", "-") for k in keys]
    table = {k.replace("_", "-"): getattr(pricing_model, k) for k in keys}
    logger.info(f"openai api pricing table:{table}")
    return table


"""
TODO rate limit using model_name,
and retry exponentially.
"""


class StructuredLLMNoneException(Exception):
    def __init__(self, message, completion):
        super().__init__(message)
        self.completion = completion


@instance
def __openai_call_stat__():
    return dict()

class StructuredLLMRefusalException(Exception):
    def __init__(self, message, completion):
        super().__init__(message)
        self.completion = completion

@injected
async def a_call_openai_api(
    a_repeat_for_rate_limit,
    a_enable_cost_logging,
    a_chat_completion_to_cost,
    __openai_call_stat__,
    /,
    api_object: Callable[[...], Awaitable],
    api_kwargs: dict,
) -> ChatCompletionWithCost:
    await a_enable_cost_logging()
    async def task():
        __openai_call_stat__["total_calls"] = (
            __openai_call_stat__.get("total_calls", 0) + 1
        )
        chat_completion = await api_object(**api_kwargs)
        cost: ChatCompletionWithCost = await a_chat_completion_to_cost(chat_completion)
        chat_completion_costs_subject.on_next(cost)
        __openai_call_stat__["total_cost_usd"] = (
            __openai_call_stat__.get("total_cost_usd", 0) + cost.total_cost_usd
        )
        cumulative_cost = __openai_call_stat__["total_cost_usd"]
        logger.info(
            f"cost: {cost.total_cost_usd:.4f} USD, cumulative: {cumulative_cost:.4f} USD"
        )
        refusal = chat_completion.choices[0].message.refusal # ココ
        if refusal is not None:
            raise StructuredLLMRefusalException(f"refusal from llm:{refusal}", cost)
        return cost

    return await a_repeat_for_rate_limit(task)


@injected
async def a_vision_llm__openai(
    async_openai_client: AsyncOpenAI,
    logger,
    a_call_openai_api,
    /,
    text: str,
    images: Optional[list[Image]] = None,
    model: str = "gpt-4o",
    max_tokens=None,  # deprecated
    max_completion_tokens=None,  # same as max_tokens
    response_format: openai.types.chat.completion_create_params.ResponseFormat = None,
    detail: Literal["auto", "low", "high"] = "auto",
    reasoning_effort: Literal["low", "medium", "high"] = None,
) -> str:
    if max_completion_tokens is None:
        if max_tokens is None:
            max_completion_tokens = 2048
        max_completion_tokens = max_tokens

    assert isinstance(async_openai_client, AsyncOpenAI)
    if images is None:
        images = []
    if response_format is None:
        response_format = {"type": "text"}

    for img in images:
        assert isinstance(img, Image), f"image is not Image, but {type(img)}"

    if isinstance(response_format, type) and issubclass(response_format, BaseModel):
        API = async_openai_client.beta.chat.completions.parse

        def get_result(completion):
            data = completion.choices[0].message.parsed
            if data is None:
                raise StructuredLLMNoneException("data from llm is None", completion)
            logger.info(completion)
            return data

    else:
        API = async_openai_client.chat.completions.create

        def get_result(completion:ChatCompletion):
            return completion.choices[0].message.content

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
        max_completion_tokens=max_completion_tokens,
        response_format=response_format,
    )
    if reasoning_effort is not None:
        api_kwargs["reasoning_effort"] = reasoning_effort

    @retry(
        retry=retry_if_exception_type(StructuredLLMRefusalException),
        stop=stop_after_attempt(3),
    )
    async def task():
        chat_completion: ChatCompletionWithCost = await a_call_openai_api(
            api_object=API, api_kwargs=api_kwargs
        )
        return get_result(chat_completion.src)
    return await task()


@instance
async def cost_logging_state():
    return dict(
        enabled=False,
    )


@injected
async def a_enable_cost_logging(
    cost_logging_state: dict, chat_completion_costs_subject: reactivex.Subject, /
):
    if cost_logging_state["enabled"]:
        return
    cumulative_cost = 0

    def on_next(cost: ChatCompletionWithCost):
        nonlocal cumulative_cost
        cumulative_cost += cost.total_cost_usd
        logger.info(
            f"cost: {cost.total_cost_usd:.4f} USD, cumulative: {cumulative_cost:.4f} USD"
        )

    chat_completion_costs_subject.subscribe(on_next)
    cost_logging_state["enabled"] = True


a_vision_llm__gpt4o = Injected.partial(a_vision_llm__openai, model="gpt-4o")
_test_a_gpt4o: Injected = Injected.procedure(
    a_enable_cost_logging(),
    a_vision_llm__gpt4o("hello?"),
    a_vision_llm__gpt4o("hello hello"),
)
a_vision_llm__gpt4 = Injected.partial(
    a_vision_llm__openai, model="gpt-4-vision-preview"
)
a_cached_vision_llm__gpt4o = async_cached(
    sqlite_dict(
        str(Path("~/.cache/pinjected_openai/a_vision_llm__gpt4o.sqlite").expanduser())
    )
)(a_vision_llm__gpt4o)
a_cached_vision_llm__gpt4 = async_cached(
    sqlite_dict(
        str(Path("~/.cache/pinjected_openai/a_vision_llm__gpt4.sqlite").expanduser())
    )
)(a_vision_llm__gpt4)

a_llm_gpto3_mini = Injected.partial(
    a_vision_llm__openai, model="o3-mini"
)

test_a_llm_gpto3_mini:IProxy = a_llm_gpto3_mini('hello')


@injected
async def a_llm__openai(
    async_openai_client: AsyncOpenAI,
    a_repeat_for_rate_limit,
    a_enable_cost_logging,
    /,
    text: str,
    model_name: str,
    max_completion_tokens=4096,
) -> str:
    assert isinstance(async_openai_client, AsyncOpenAI)
    await a_enable_cost_logging()

    async def task():
        # import tiktoken
        # enc = tiktoken.get_encoding("cl100k_base")
        # n_token = len(enc.encode(text))
        chat_completion = await async_openai_client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": text},
                    ],
                }
            ],
            model=model_name,
            max_tokens=max_completion_tokens,
        )
        return chat_completion

    chat_completion = await a_repeat_for_rate_limit(task)
    res = chat_completion.choices[0].message.content
    assert isinstance(res, str)
    logger.info(f"result:\n{res}")
    return res


@injected
async def a_llm__gpt4_turbo(
    a_llm__openai, /, text: str, max_completion_tokens=4096
) -> str:
    return await a_llm__openai(
        text,
        max_completion_tokens=max_completion_tokens,
        model_name="gpt-4-turbo-preview",
    )


a_llm__gpt4_turbo_cached = async_cached(
    sqlite_dict(str(Path("~/.cache/a_llm__gpt4_turbo.sqlite").expanduser()))
)(a_llm__gpt4_turbo)


@injected
async def a_llm__gpt35_turbo(
    a_llm__openai, /, text: str, max_completion_tokens=4096
) -> str:
    return await a_llm__openai(
        text, max_completion_tokens=max_completion_tokens, model_name="gpt-3.5-turbo"
    )


@injected
async def a_json_llm__openai(
    logger,
    async_openai_client: AsyncOpenAI,
    a_repeat_for_rate_limit,
    /,
    text: str,
    max_completion_tokens=4096,
    model="gpt-4-0125-preview",
) -> str:
    assert isinstance(async_openai_client, AsyncOpenAI)

    async def task():
        # import tiktoken
        # enc = tiktoken.get_encoding("cl100k_base")
        # n_token = len(enc.encode(text))
        chat_completion = await async_openai_client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": text},
                    ],
                }
            ],
            model=model,
            max_tokens=max_completion_tokens,
            response_format={"type": "json_object"},
        )
        return chat_completion

    chat_completion = await a_repeat_for_rate_limit(task)
    res = chat_completion.choices[0].message.content
    assert isinstance(res, str)
    logger.info(f"\n{res}")
    return json.loads(res)


@injected
async def a_json_llm__gpt4_turbo(
    a_json_llm__openai, /, text: str, max_completion_tokens=4096
) -> str:
    return await a_json_llm__openai(
        text=text,
        max_completion_tokens=max_completion_tokens,
        model="gpt-4-turbo-preview",
    )


@injected
async def a_vlm__openai_batched(
    async_openai_client: AsyncOpenAI,
    a_repeat_for_rate_limit,
    a_enable_cost_logging,
    /,
    texts: list[str],
    model_name: str,
    max_completion_tokens=4096,
) -> list[str]:
    assert isinstance(async_openai_client, AsyncOpenAI)
    await a_enable_cost_logging()

    async def task():
        completions = await async_openai_client.chat.completions.create_batch(
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": text},
                    ],
                }
                for text in texts
            ],
            model=model_name,
            max_tokens=max_completion_tokens,
        )
        return [c.choices[0].message.content for c in completions]

    completions = await a_repeat_for_rate_limit(task)
    return completions


test_vision_llm__gpt4 = a_vision_llm__gpt4(
    text="What are inside this image?",
    images=Injected.list(),
)
"""
('The image appears to be an advertisement or an informational graphic about '
 'infant and newborn nutrition. It features a baby with light-colored hair who '
 'is lying down and holding onto a baby bottle, seemingly feeding themselves. '
 'The baby is looking directly towards the camera. The image uses a soft pink '
 'color palette, which is common for baby-related products or information. '
 'There are texts that read "Infant & Newborn Nutrition" and "Absolutely New," '
 'along with the word "PINGUIN" at the top, which could be a brand name or '
 "logo. The layout and design of this image suggest it's likely used for "
 'marketing purposes or as part of educational material regarding baby '
 'nutrition.')
"""

test_llm__gpt4_turbo = a_llm__gpt4_turbo("Hello world")

test_json_llm__gpt4_turbo = a_json_llm__gpt4_turbo("Hello world, respond to me in json")

__meta_design__ = instances()
