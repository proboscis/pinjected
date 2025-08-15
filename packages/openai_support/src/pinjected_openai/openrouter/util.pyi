from typing import overload, Any, Literal, TYPE_CHECKING
from pinjected import IProxy
from pydantic import BaseModel
from openai.types import CompletionUsage
import PIL.Image
from returns.result import ResultE

if TYPE_CHECKING:
    from pinjected_openai.openrouter.instances import StructuredLLM

class SimpleLlmProtocol:
    async def __call__(self, prompt: str) -> Any: ...

class AOpenrouterPostProtocol:
    async def __call__(self, payload: dict) -> dict: ...

class ACachedSchemaExampleProviderProtocol:
    async def __call__(self, model_schema: dict) -> Any: ...

class AOpenrouterBaseChatCompletionProtocol:
    async def __call__(
        self,
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
    ) -> Any: ...

class AResizeImageBelow5mbProtocol:
    async def __call__(self, img: PIL.Image.Image) -> PIL.Image.Image: ...

class AOpenrouterChatCompletionProtocol:
    async def __call__(
        self,
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
    ) -> Any: ...

class ALlmOpenrouterProtocol:
    async def __call__(
        self, text: str, model: str, response_format=..., **kwargs
    ) -> Any: ...

@overload
async def a_openrouter_post(payload: dict) -> IProxy[dict]: ...
@overload
async def a_cached_schema_example_provider(model_schema: dict) -> IProxy[Any]: ...
@overload
async def a_openrouter_base_chat_completion(
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

test_call_gpt4o: Any

test_openai_compatible_llm: Any

test_openrouter_text: Any

test_openrouter_structure: Any

test_openrouter_model_table: Any

test_openrouter_chat_completion: Any

test_openrouter_chat_completion_with_structure: Any

test_openrouter_chat_completion_with_structure_optional: Any

test_gemini_pro_with_incompatible_schema: Any

test_gemini_flash_with_incompatible_schema: Any

test_gemini_flash_with_compatible_schema: Any

test_is_openapi3_compatible: Any

test_is_openapi3_compatible_optional: Any

test_is_gemini_compatible: Any

test_is_gemini_compatible_optional: Any

test_is_gemini_compatible_union: Any

test_is_gemini_compatible_dict: Any

test_is_gemini_compatible_complex_key_dict: Any

test_is_gemini_compatible_complex_value_dict: Any

test_is_gemini_compatible_complex_list: Any

test_return_empty_item: Any

test_resize_image: Any

test_model_supports_json: Any

test_model_no_json_support: Any

test_completion_no_json_support: Any

test_completion_with_json_support: Any

test_reasoning_simple: Any

test_reasoning_with_structure: Any

test_reasoning_advanced: Any

test_reasoning_exclude: Any

openrouter_model_table: Any

openrouter_api: Any

openrouter_state: Any

openrouter_timeout_sec: Any

def handle_openrouter_error(res: dict, logger) -> None: ...
def extract_json_from_markdown(data: str) -> str: ...
def parse_json_response(*args, **kwargs) -> Any: ...
def update_cumulative_cost(
    openrouter_state: dict, cost_dict: ResultE[dict]
) -> None: ...
def build_openrouter_response_format(*args, **kwargs) -> Any: ...
def is_openapi3_compatible(*args, **kwargs) -> Any: ...
def is_gemini_compatible(*args, **kwargs) -> Any: ...

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
    supported_parameters: list[str] | None
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
    json: bool  # Kept for backward compatibility (alias)
    json_output: bool  # New field name
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
    def calc_cost(self, usage: CompletionUsage) -> Any: ...
    def calc_cost_dict(self, usage: dict) -> Any: ...

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

class OpenRouterChatCompletion:
    async def __call__(
        self,
        prompt: str,
        model: str,
        max_tokens: int = ...,
        temperature: float = ...,
        images: list[PIL.Image.Image] | None = ...,
        response_format: BaseModel | None = ...,
        provider: dict[Any] | None = ...,
        **kwargs,
    ) -> Any: ...

__openapi3_compatibility_cache: Any

__gemini_compatibility_cache: Any

__design__: Any

__debug_design: Any

async def parse_json_response(*args, **kwargs) -> Any: ...
async def setup_response_format(
    response_format: type[BaseModel] | None,
    model: str,
    prompt: str,
    provider_filter: dict[Any],
    logger: Any,
    openrouter_model_table: OpenRouterModelTable,
    a_cached_schema_example_provider: ACachedSchemaExampleProviderProtocol,
) -> tuple[Any]: ...
async def handle_structured_response(
    data: str,
    response_format: type[BaseModel] | None,
    prompt: str,
    use_json_fix_fallback: bool,
    logger: Any,
    a_structured_llm_for_json_fix: StructuredLLM,
) -> Any: ...

class OpenRouterOverloadedError: ...
class OpenRouterTransientError: ...

def calculate_cumulative_cost(
    openrouter_state: dict, cost_dict: ResultE[dict]
) -> dict: ...

class LoggerProtocol:
    def info(self, message: str) -> None: ...
    def warning(self, message: str) -> None: ...
    def error(self, message: str) -> None: ...
    def success(self, message: str) -> None: ...

class OpenRouterAPIProtocol:
    def __init__(self, base_url: str, api_key: str) -> None: ...

# Additional symbols:
def validate_response_format(response_format: type[BaseModel], model: str) -> None: ...
def build_provider_filter(provider: dict | None = ...) -> dict: ...
def build_user_message(
    prompt: str, images: list[PIL.Image.Image] | None = ...
) -> dict: ...
def build_chat_payload(
    model: str,
    prompt: str,
    max_tokens: int,
    temperature: float,
    images: list[PIL.Image.Image] | None = ...,
    provider: dict | None = ...,
    include_reasoning: bool = ...,
    reasoning: dict | None = ...,
    **kwargs,
) -> dict: ...
def log_completion_cost(
    res: dict,
    model: str,
    openrouter_model_table: OpenRouterModelTable,
    openrouter_state: dict,
    logger: LoggerProtocol,
) -> None: ...

# Additional symbols:
def prepare_json_provider_and_kwargs(
    provider: dict | None,
    kwargs: dict,
    response_format: type[BaseModel],
    supports_json: bool,
    logger: LoggerProtocol,
    model: str,
) -> JsonProviderConfig: ...

class JsonProviderConfig:
    provider: dict | None
    kwargs: dict

# Additional symbols:

# Additional symbols:

# Additional symbols:
_models_with_false_json_claims: set[str]

def clear_false_json_claims_cache() -> Any: ...
