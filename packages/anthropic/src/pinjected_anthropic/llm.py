import asyncio
import base64
import io
from asyncio import Lock
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Literal, Callable, Awaitable, TypeVar

import PIL
import pandas as pd
from PIL import Image
from anthropic import AsyncAnthropic, Stream
from anthropic import RateLimitError, InternalServerError
from anthropic.types import Message, MessageStartEvent, ContentBlockStartEvent, ContentBlockDeltaEvent, Usage
from pinjected import *


@instance
async def anthropic_client(anthropic_api_key):
    return AsyncAnthropic(api_key=anthropic_api_key)


IMAGE_FORMAT = Literal['jpeg', 'png']


class AnthropicClientCallback:
    async def __call__(self, response):
        pass


@injected
async def a_anthropic_llm(
        anthropic_client,
        /,
        messages: list[dict],
        max_tokens=1024,
        # model="claude-3-opus-20240229"
        model="claude-3-5-sonnet-20240620"
) -> Message:
    msg = await anthropic_client.messages.create(
        max_tokens=max_tokens,
        model=model,
        messages=messages
    )
    return msg


def image_to_base64(image: PIL.Image.Image, fmt: IMAGE_FORMAT) -> str:
    assert isinstance(image, PIL.Image.Image), f"image is not an instance of PIL.Image.Image: {image}"
    bytes_io = io.BytesIO()
    image.save(bytes_io, format=fmt)
    bytes_io.seek(0)
    data = base64.b64encode(bytes_io.getvalue()).decode('utf-8')
    assert data, "data is empty"
    return data


"""


import anthropic

client = anthropic.Anthropic()
message = client.messages.create(
    model="claude-3-5-sonnet-20240620",
    max_tokens=1024,
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": image1_media_type,
                        "data": image1_data,
                    },
                },
                {
                    "type": "text",
                    "text": "Describe this image."
                }
            ],
        }
    ],
)
print(message)
"""


@dataclass
class UsageEntry:
    timestamp: pd.Timestamp
    tokens: int

    class Config:
        arbitrary_types_allowed = True


@dataclass
class RateLimitManager:
    max_tokens: int
    max_calls: int
    duration: pd.Timedelta
    lock: Lock = asyncio.Lock()
    call_history: list[UsageEntry] = field(default_factory=list)

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
            remaining = await self._remaining_tokens()
            is_ready = remaining >= token and len(self.call_history) < self.max_calls
            if is_ready:
                self.call_history.append(UsageEntry(pd.Timestamp.now(), token))
            return is_ready

    async def _remaining_tokens(self):
        return self.max_tokens - await self._current_usage()

    async def _current_usage(self):
        t = pd.Timestamp.now()
        self.call_history = [e for e in self.call_history if e.timestamp > t - self.duration]
        return sum(e.tokens for e in self.call_history)


@dataclass
class AnthropicRateLimitController:
    manager_factory: Callable[[str], Awaitable[RateLimitManager]]
    managers: dict[str, RateLimitManager] = field(default_factory=dict)
    lock: Lock = asyncio.Lock()

    async def get_manager(self, key):
        async with self.lock:
            if key not in self.managers:
                self.managers[key] = await self.manager_factory(key)
            return self.managers[key]


@instance
async def anthropic_rate_limit_controller():
    async def factory(key: str):
        if 'sonnet' in key and '3_5' in key:
            return RateLimitManager(
                max_tokens=40000,
                max_calls=50,
                duration=pd.Timedelta(minutes=1),
            )
        elif 'opus' in key and '3' in key:
            return RateLimitManager(
                max_tokens=20000,
                max_calls=50,
                duration=pd.Timedelta(minutes=1),
            )
        elif 'sonnet' in key and '3' in key:
            return RateLimitManager(
                max_tokens=40000,
                max_calls=50,
                duration=pd.Timedelta(minutes=1),
            )
        elif 'haiku' in key and '3' in key:
            return RateLimitManager(
                max_tokens=50000,
                max_calls=50,
                duration=pd.Timedelta(minutes=1),
            )
        else:
            return RateLimitManager(
                max_tokens=20000,
                max_calls=50,
                duration=pd.Timedelta(minutes=1),
            )

    return AnthropicRateLimitController(factory)


def count_image_token(img: PIL.Image.Image):
    w, h = img.size
    tokens = (w * h) / 750
    return tokens


@dataclass
class ModelPriceTable:
    usd_per_million_input_token: float
    usd_per_million_output_token: float
    usd_per_million_cache_write: float
    usd_per_million_cache_read: float


class AnthropicModelPrices:
    # Claude 3.5 Sonnet prices
    claude__3_5_20241022 = ModelPriceTable(
        usd_per_million_input_token=3.0,
        usd_per_million_output_token=15.0,
        usd_per_million_cache_write=3.75,
        usd_per_million_cache_read=0.30
    )

    # Claude 3.5 Haiku prices
    claude__3_5_haiku = ModelPriceTable(
        usd_per_million_input_token=1.0,
        usd_per_million_output_token=5.0,
        usd_per_million_cache_write=1.25,
        usd_per_million_cache_read=0.10
    )

    # Claude 3 Opus prices
    claude__3_opus = ModelPriceTable(
        usd_per_million_input_token=15.0,
        usd_per_million_output_token=75.0,
        usd_per_million_cache_write=18.75,
        usd_per_million_cache_read=1.50
    )
    claude__3_sonnet_20240229 = ModelPriceTable(
        usd_per_million_input_token=3.0,
        usd_per_million_output_token=15.0,
        usd_per_million_cache_write=3.75, # should be NaN
        usd_per_million_cache_read=0.30 # should be NaN
    )
    model_prices = {
        "claude-3-5-sonnet-20241022": claude__3_5_20241022,
        "claude-3-5-haiku": claude__3_5_haiku,
        "claude-3-opus": claude__3_opus,
        "claude-3-sonnet-20240229": claude__3_sonnet_20240229
    }

    def __getitem__(self, item):
        return self.model_prices[item]


@instance
async def anthropic_model_prices():
    return AnthropicModelPrices()


@dataclass
class AnthropicCumulativeUsageTracker:
    _anthropic_model_prices: AnthropicModelPrices
    usages: dict[Usage] = field(default_factory=lambda: defaultdict(list))

    def add_usage(self, model, usage: Usage):
        self.usages[model].append(usage)

    def usage_text(self):
        result = ""
        import pandas as pd
        for model in self.usages:
            usage_df = pd.DataFrame([u.dict() for u in self.usages[model]])
            table = self._anthropic_model_prices[model]
            usage_df['input_cost'] = usage_df['input_tokens'] * table.usd_per_million_input_token / 1_000_000
            usage_df['output_cost'] = usage_df['output_tokens'] * table.usd_per_million_output_token / 1_000_000
            desc = usage_df.describe()
            desc.loc['total'] = usage_df.sum()
            result += f"Model: {model}\n"
            result += desc.to_string()
            result += "\n"
        return result


@instance
async def anthropic_cumulative_usage_tracker(anthropic_model_prices):
    return AnthropicCumulativeUsageTracker(anthropic_model_prices)


@injected
async def anthropic_client_callback(
        logger,
        anthropic_cumulative_usage_tracker: AnthropicCumulativeUsageTracker,
        /,
        response: Message):
    """
    override this via design so that you can do something with the response globally, like logging, or cost tracking
    :param response:
    :return:
    """
    usage = response.usage
    anthropic_cumulative_usage_tracker.add_usage(response.model, usage)
    logger.info(f"Anthropic usage:\n{anthropic_cumulative_usage_tracker.usage_text()}")


BaseModelType = TypeVar('T')

from pydantic import BaseModel


class TestClass(BaseModel):
    pass


class IMessageProcessor:
    def prepare_messages(self, text, images, img_format: IMAGE_FORMAT, response_format) -> list[dict]:
        pass

    def process_response(self, response, response_format):
        pass


@injected
def prepare_messages__common(text, images, img_format: Literal['jpeg']):
    img_blocks = []
    if images is not None:
        for img in images:
            if img_format == 'jpeg':
                img = img.convert('RGB')
            block = {
                'type': 'image',
                'source': {
                    'type': 'base64',
                    'media_type': f"image/{img_format}",
                    'data': image_to_base64(img, img_format),
                }
            }
            img_blocks.append(block)

    messages = [
        {
            'content': [
                *img_blocks,
                {
                    'type': 'text',
                    'text': text
                },
            ],
            'role': "user"
        },
    ]
    return messages


@injected
def prepare_messages__pydantic(
        prepare_messages__common,
        /,
        text, images, img_format, type_var):
    schema = type_var.model_json_schema()
    messages = prepare_messages__common(text, images, img_format=img_format)
    contents = messages[0]['content']
    prompt = text + f"""
The answer must follow the following json schema:
```json
{schema}
```
"""
    contents[-1] = {
        'type': 'text',
        'text': prompt
    }
    messages.append({
        'role': 'assistant',
        'content': 'Here is the JSON answer:\n {'
    })
    return messages


@instance
def message_processor__common(
        prepare_messages__common,
        /,
):
    class CommonMessageProcessor(IMessageProcessor):
        def prepare_messages(self, text, images, img_format: IMAGE_FORMAT, response_format) -> list[dict]:
            return prepare_messages__common(text, images, img_format)

        def process_response(self, response, response_format):
            return response.content[-1].text

    return CommonMessageProcessor()


@instance
def message_processor__pydantic(
        prepare_messages__pydantic,
        /,
):
    class PydanticMessageProcessor(IMessageProcessor):
        def prepare_messages(self, text, images, img_format: IMAGE_FORMAT, response_format) -> list[dict]:
            return prepare_messages__pydantic(text, images, img_format=img_format, type_var=response_format)

        def process_response(self, response, response_format):
            json = '{' + response.content[-1].text
            json_end = json.rfind('}')
            json = json[:json_end + 1]
            return response_format.model_validate_json(json)

    return PydanticMessageProcessor()


@injected
async def a_vision_llm__anthropic(
        message_processor__common: IMessageProcessor,
        message_processor__pydantic: IMessageProcessor,
        anthropic_client: AsyncAnthropic,
        logger,
        anthropic_rate_limit_controller: AnthropicRateLimitController,
        anthropic_client_callback: AnthropicClientCallback,
        /,
        text: str,
        images: list[PIL.Image.Image] = None,
        model="claude-3-5-sonnet-20241022",
        max_tokens: int = 2048,
        img_format: IMAGE_FORMAT = 'jpeg',
        response_format: BaseModelType | Literal['text'] = "text"
) -> str | BaseModelType:
    if response_format == 'text':
        message_processor = message_processor__common
    elif isinstance(response_format, type) and issubclass(response_format, BaseModel):
        message_processor = message_processor__pydantic
    else:
        raise RuntimeError(f"Invalid response format {response_format}")

    messages = message_processor.prepare_messages(text, images, img_format, response_format)

    expected_tokens = await anthropic_client.beta.messages.count_tokens(
        messages=messages,
        model=model
    )
    expected_tokens = expected_tokens.input_tokens

    async def attempt():
        msg: Message = await anthropic_client.messages.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens
        )

        return msg

    manager: RateLimitManager = await anthropic_rate_limit_controller.get_manager(model)
    from anthropic import APIConnectionError
    while True:
        try:
            await manager.acquire(expected_tokens)
            resp = await attempt()
            await anthropic_client_callback(resp)
            return message_processor.process_response(resp, response_format)
        except RateLimitError as rle:
            logger.warning(f"Rate limit error for model {model}, waiting for {5} seconds :\n{rle}")
            await asyncio.sleep(5)
        except InternalServerError as ise:
            logger.warning(f"Rate limit error for model {model}, waiting for {5} seconds :\n{ise}")
            await asyncio.sleep(10)
        except APIConnectionError as ace:
            logger.warning(f"API connection error for model {model}, waiting for {5} seconds :\n{ace}")
            await asyncio.sleep(10)


@injected
async def a_anthropic_llm_stream(
        anthropic_client,
        /,
        messages: list[dict],
        max_tokens=1024,
        model="claude-3-opus-20240229"
) -> Stream:
    msg = await anthropic_client.messages.create(
        max_tokens=max_tokens,
        model=model,
        messages=messages,
        stream=True
    )
    async for item in msg:
        match item:
            case MessageStartEvent():
                pass
            case ContentBlockStartEvent():
                pass
            case ContentBlockDeltaEvent() as cbde:
                yield cbde.delta.text


test_run_opus: Injected = a_anthropic_llm(
    messages=[
        {
            "content": "What is the meaning of life?",
            "role": "user"
        }
    ],
)

test_a_vision_llm: IProxy = a_vision_llm__anthropic(
    text="What is the meaning of life?",
    images=[],
)


class MeaningOfLife(BaseModel):
    meaning: str


test_a_vision_llm__structured: IProxy = a_vision_llm__anthropic(
    text="What is the meaning of life?",
    response_format=MeaningOfLife
)
sample_image = injected(Image.open)("test_image/test1.jpg")
test_to_base64: IProxy = injected(image_to_base64)(sample_image, 'jpeg')

test_a_vision_llm_with_image: IProxy = a_vision_llm__anthropic(
    text="What do you see in this image?",
    images=Injected.list(
        injected(Image.open)("test_image/test1.jpg")
    ),
)


class ImageContent(BaseModel):
    content: str


test_a_vision_llm_with_image__structured: IProxy = a_vision_llm__anthropic(
    text="What do you see in this image?",
    images=Injected.list(
        injected(Image.open)("test_image/test1.jpg")
    ),
    response_format=ImageContent
)


@instance
async def test_run_opus_stream(a_anthropic_llm_stream):
    stream = a_anthropic_llm_stream(
        messages=[
            {
                "content": "What is the meaning of life?",
                "role": "user"
            }
        ],
    )
    async for msg in stream:
        print(msg)


a_vision_llm__claude_3_5_20241022 = Injected.partial(a_vision_llm__anthropic, model="claude-3-5-sonnet-20241022")

__meta_design__ = instances(
)
