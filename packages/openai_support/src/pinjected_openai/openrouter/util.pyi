from typing import overload, Any, Literal, Protocol
from pinjected import IProxy
from pydantic import BaseModel
from openai.types import CompletionUsage
from returns.result import ResultE
import PIL.Image

class SimpleLlmProtocol(Protocol):
    async def __call__(self, prompt: str) -> Any: ...

class AOpenrouterPostProtocol(Protocol):
    async def __call__(self, payload: dict) -> dict: ...

class ACachedSchemaExampleProviderProtocol(Protocol):
    async def __call__(self, model_schema: dict) -> Any: ...

class AOpenrouterChatCompletionWithoutFixProtocol(Protocol):
    async def __call__(
        self,
        prompt: str,
        model: str,
        max_tokens: int = ...,
        temperature: float = ...,
        images: list[PIL.Image.Image] | None = ...,
        response_format=...,
        provider: dict | None = ...,
        **kwargs,
    ) -> Any: ...

class AResizeImageBelow5mbProtocol(Protocol):
    async def __call__(self, img: PIL.Image.Image) -> PIL.Image.Image: ...

class AOpenrouterChatCompletionProtocol(Protocol):
    async def __call__(
        self,
        prompt: str,
        model: str,
        max_tokens: int = ...,
        temperature: float = ...,
        images: list[PIL.Image.Image] | None = ...,
        response_format=...,
        provider: dict | None = ...,
        **kwargs,
    ) -> Any: ...

class ALlmOpenrouterProtocol(Protocol):
    async def __call__(
        self, text: str, model: str, response_format=..., **kwargs
    ) -> Any: ...

@overload
async def a_openrouter_post(payload: dict) -> IProxy[dict]: ...
@overload
async def a_cached_schema_example_provider(model_schema: dict) -> IProxy[Any]: ...
@overload
async def a_openrouter_chat_completion__without_fix(
    prompt: str,
    model: str,
    max_tokens: int = ...,
    temperature: float = ...,
    images: list[PIL.Image.Image] | None = ...,
    response_format=...,
    provider: dict | None = ...,
    include_reasoning: bool = ...,
    reasoning: dict | None = ...,
    **kwargs,
) -> IProxy[Any]: ...
@overload
async def a_resize_image_below_5mb(img: PIL.Image.Image): ...
@overload
async def a_openrouter_chat_completion(
    prompt: str,
    model: str,
    max_tokens: int = ...,
    temperature: float = ...,
    images: list[PIL.Image.Image] | None = ...,
    response_format=...,
    provider: dict | None = ...,
    include_reasoning: bool = ...,
    reasoning: dict | None = ...,
    **kwargs,
): ...
@overload
async def a_llm__openrouter(text: str, model: str, response_format=..., **kwargs): ...

test_call_gpt4o: IProxy[Any]

test_openai_compatible_llm: IProxy[Any]

test_openrouter_text: IProxy[Any]

test_openrouter_structure: IProxy[Text]

test_openrouter_model_table: IProxy[OpenRouterModelTable]

test_openrouter_chat_completion: IProxy[Any]

test_openrouter_chat_completion_with_structure: IProxy[Text]

test_openrouter_chat_completion_with_structure_optional: IProxy[OptionalText]

test_gemini_pro_with_incompatible_schema: IProxy[PersonWithUnion]

test_gemini_flash_with_incompatible_schema: IProxy[PersonWithUnion]

test_gemini_flash_with_compatible_schema: IProxy[SimpleResponse]

test_is_openapi3_compatible: IProxy[dict[Any]]

test_is_openapi3_compatible_optional: IProxy[dict[Any]]

test_is_gemini_compatible: IProxy[dict[Any]]

test_is_gemini_compatible_optional: IProxy[dict[Any]]

test_is_gemini_compatible_union: IProxy[dict[Any]]

test_is_gemini_compatible_dict: IProxy[dict[Any]]

test_is_gemini_compatible_complex_key_dict: IProxy[dict[Any]]

test_is_gemini_compatible_complex_value_dict: IProxy[dict[Any]]

test_is_gemini_compatible_complex_list: IProxy[dict[Any]]

test_return_empty_item: IProxy[Text]

test_resize_image: IProxy[PIL.Image.Image]

test_model_supports_json: IProxy[bool]

test_model_no_json_support: IProxy[bool]

test_completion_no_json_support: IProxy[SimpleResponse]

test_completion_with_json_support: IProxy[SimpleResponse]
test_reasoning_simple: IProxy[Any]
test_reasoning_with_structure: IProxy[Any]
test_reasoning_advanced: IProxy[Any]
test_reasoning_exclude: IProxy[Any]

openrouter_model_table: IProxy[OpenRouterModelTable]

openrouter_api: IProxy[Any]

openrouter_state: IProxy[Any]

openrouter_timeout_sec: IProxy[float]

def handle_openrouter_error(res: dict, logger) -> None: ...
def extract_json_from_markdown(data: str) -> str: ...
def parse_json_response(
    data: str, response_format: type[BaseModel], logger=...
) -> Any: ...
def update_cumulative_cost(state: dict, cost: dict | float) -> None: ...
def build_openrouter_response_format(response_format) -> Any: ...
def is_openapi3_compatible(model: type[BaseModel]) -> dict[Any]: ...
def is_gemini_compatible(model: type[BaseModel]) -> dict[Any]: ...

class OpenRouterModelTable:
    data: list[OpenRouterModel]
    model_config: Any
    def pricing(self, model_id: str) -> OpenRouterModelPricing: ...
    def safe_pricing(self, model_id: str) -> ResultE[OpenRouterModelPricing]: ...
    def get_model(self, model_id: str) -> OpenRouterModel | None: ...
    def supports_json_output(self, model_id: str) -> bool: ...

class ContactInfoWithUnion:
    type: Literal[Any]
    value: str

class OpenRouterRateLimitError: ...

class OpenRouterModel:
    id: str
    name: str
    created: int
    description: str
    context_length: int
    architecture: OpenRouterArchitecture
    pricing: OpenRouterModelPricing
    providers: list[OpenRouterProviderInfo] | None
    top_provider: OpenRouterProviderInfo | None
    per_request_limits: dict[Any] | None
    model_config: Any
    def supports_json_output(self) -> bool: ...

class PersonWithUnion:
    name: str
    age: int
    contact: ContactInfoWithUnion | str

class ComplexValue:
    value: str
    description: str

class Text:
    text_lines: list[str]

class GeminiCompatibilityError:
    def __init__(self, model: type, issues: dict[Any]) -> Any: ...

class PersonWithComplexList:
    name: str
    age: int
    addresses: list[Address]

class PersonWithComplexDict:
    name: str
    age: int
    scores: dict[Any]

class OpenRouterCapabilities:
    vision: bool
    json: bool
    tools: bool
    model_config: Any

class SchemaCompatibilityError: ...

class OpenRouterModelPricing:
    prompt: str
    completion: str
    image: str | None
    request: str | None
    web_search: str | None
    internal_reasoning: str | None
    input_cache_read: str | None
    input_cache_write: str | None
    model_config: Any
    def calc_cost(self, usage: CompletionUsage | dict) -> Any: ...
    def calc_cost_dict(self, usage: dict) -> dict[Any]: ...

class OpenAPI3CompatibilityError:
    def __init__(self, model: type, issues: dict[Any]) -> Any: ...

class SimpleResponse:
    answer: str
    confidence: float

class PersonWithDict:
    name: str
    age: int
    attributes: dict[Any]

class PersonWithComplexValueDict:
    name: str
    age: int
    details: dict[Any]

class Address:
    street: str
    city: str
    zip_code: str

class OpenRouterArchitecture:
    modality: str
    tokenizer: str
    instruct_type: str | None
    input_modalities: list[str] | None
    output_modalities: list[str] | None
    capabilities: OpenRouterCapabilities | None
    model_config: Any

class OpenRouterTimeOutError: ...

class OpenRouterProviderInfo:
    id: str | None
    name: str | None
    parameters: dict[Any] | None
    is_moderated: bool
    context_length: int | None
    max_completion_tokens: int | None
    can_stream: bool | None
    model_config: Any

class OptionalText:
    text_lines: list[str] | None

class OpenRouterChatCompletion: ...
