from typing import overload, Any, Callable, Literal
from datetime import datetime, timedelta
from threading import Lock
import openai
from openai.types.chat import ChatCompletion
from PIL.Image import Image
from pinjected import IProxy

# IMPORTANT: @injected functions MUST use @overload in .pyi files
# The @overload decorator is required to properly type-hint the user-facing interface
# This allows IDEs to show only runtime arguments (after /) to users
# DO NOT change @overload to @injected - this is intentional for IDE support

@overload
async def a_repeat_for_rate_limit(task): ...
@overload
def openai_count_image_tokens(width: int, height: int): ...
@overload
async def a_chat_completion_to_cost(
    completion: ChatCompletion,
) -> IProxy[ChatCompletionWithCost]: ...
@overload
async def a_call_openai_api(
    api_object: Callable[Any], api_kwargs: dict
) -> IProxy[ChatCompletionWithCost]: ...
@overload
async def a_vision_llm__openai(
    text: str,
    images: list[Image] | None = ...,
    model: str = ...,
    max_tokens=...,
    max_completion_tokens=...,
    response_format: openai.types.chat.completion_create_params.ResponseFormat = ...,
    detail: Literal["auto", "low", "high"] = ...,
    reasoning_effort: Literal["low", "medium", "high"] | None = ...,
) -> IProxy[str]: ...
@overload
async def a_enable_cost_logging(): ...
@overload
async def a_llm__openai(
    text: str, model_name: str, max_completion_tokens=...
) -> IProxy[str]: ...
@overload
async def a_llm__gpt4_turbo(text: str, max_completion_tokens=...) -> IProxy[str]: ...
@overload
async def a_llm__gpt35_turbo(text: str, max_completion_tokens=...) -> IProxy[str]: ...
@overload
async def a_json_llm__openai(
    text: str, max_completion_tokens=..., model=...
) -> IProxy[str]: ...
@overload
async def a_json_llm__gpt4_turbo(
    text: str, max_completion_tokens=...
) -> IProxy[str]: ...
@overload
async def a_vlm__openai_batched(
    texts: list[str], model_name: str, max_completion_tokens=...
) -> IProxy[list[str]]: ...

# Additional symbols:

personal_limits: Any
pricing_model: Any
a_vision_llm__gpt4o: Any
a_vision_llm__gpt4: Any
a_cached_vision_llm__gpt4o: Any
a_cached_vision_llm__gpt4: Any
a_llm_gpto3_mini: Any
test_a_llm_gpto3_mini: IProxy
a_llm__gpt4_turbo_cached: Any
test_vision_llm__gpt4: Any
test_llm__gpt4_turbo: IProxy[Any]
test_json_llm__gpt4_turbo: IProxy[Any]

chat_completion_costs_subject: IProxy[Any]
openai_rate_limit_managers: IProxy[dict[Any, RateLimitManager]]
openai_model_pricing_table: IProxy[Any]
cost_logging_state: IProxy[Any]

def to_content(img: Image, detail: Literal["auto", "low", "high"] = ...) -> Any: ...
def resize(width, height) -> Any: ...

class BatchQueueLimits:
    tpm: int
    rpm: int
    tpd: int
    images_per_minute: int

class Limits:
    gpt_4: ModelLimits
    gpt_3_5_turbo: ModelLimits
    gpt_4_turbo: ModelLimits
    text_embedding_3_small: ModelLimits
    dall_e_3: ModelLimits
    tts_1: ModelLimits
    whisper_1: ModelLimits

class ChatCompletionWithCost:
    src: ChatCompletion
    total_cost_usd: float
    prompt_cost_usd: float
    completion_cost_usd: float

class RateLimitKey:
    api_key: str
    organization: str
    model_name: str
    request_type: str

class ModelLimits:
    modeltoken_limits: int
    request_limits: int
    other_limits: int
    batch_queue_limits: BatchQueueLimits

class UsageEntry:
    timestamp: datetime
    tokens: int

    class Config:
        arbitrary_types_allowed: Any

class ModelPricing:
    input_cost: float
    output_cost: float

class RateLimitManager:
    max_tokens: int
    max_calls: int
    duration: timedelta
    lock: Lock
    call_history: list[UsageEntry]
    async def acquire(self, approx_tokens) -> Any: ...
    async def ready(self, token) -> Any: ...
    async def remaining_tokens(self) -> Any: ...
    async def remaining_calls(self) -> Any: ...

    class Config:
        arbitrary_types_allowed: Any

class PricingModel:
    gpt_4_turbo: ModelPricing
    gpt_4_turbo_2024_04_09: ModelPricing
    gpt_4: ModelPricing
    gpt_4_32k: ModelPricing
    gpt_4_0125_preview: ModelPricing
    gpt_4_1106_preview: ModelPricing
    gpt_4_vision_preview: ModelPricing
    gpt_3_5_turbo_1106: ModelPricing
    gpt_3_5_turbo_0613: ModelPricing
    gpt_3_5_turbo_16k_0613: ModelPricing
    gpt_3_5_turbo_0301: ModelPricing
    davinci_002: ModelPricing
    babbage_002: ModelPricing
    gpt_4o_mini_2024_07_18: ModelPricing
    gpt_4o: ModelPricing
    gpt_4o_2024_05_13: ModelPricing
    gpt_4o_2024_08_06: ModelPricing
    o3_mini_2025_01_31: ModelPricing
    o1_2024_12_17: ModelPricing

class StructuredLLMNoneException:
    def __init__(self, message, completion) -> Any: ...

class StructuredLLMRefusalException:
    def __init__(self, message, completion) -> Any: ...
