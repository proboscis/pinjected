import inspect
from pprint import pformat
from typing import (
    Any,
    Literal,
    Protocol,
    Union,
    get_args,
    get_origin,
    TYPE_CHECKING,
)

if TYPE_CHECKING:
    from pinjected_openai.openrouter.instances import StructuredLLM

import httpx
import json_repair
import PIL
from injected_utils.injected_cache_utils import async_cached, sqlite_dict
from openai import AsyncOpenAI
from openai.types import CompletionUsage
from openai.types.chat import ChatCompletion
from pinjected import Injected, IProxy, design, injected, instance
from pinjected_openai.compatibles import (
    a_openai_compatible_llm,
    AOpenaiCompatibleLlmProtocol,
)
from pinjected_openai.vision_llm import to_content
from pydantic import BaseModel, ValidationError
from returns.result import ResultE, safe
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)


# Custom exceptions for schema compatibility issues
class SchemaCompatibilityError(Exception):
    """Base exception for schema compatibility issues."""


class OpenAPI3CompatibilityError(SchemaCompatibilityError):
    """Exception raised when a schema is not compatible with OpenAPI 3.0."""

    def __init__(self, model: type, issues: dict[str, list[str]]):
        self.model = model
        self.issues = issues
        message = (
            f"OpenAPI 3.0 compatibility issues found in {model.__name__}: {issues}"
        )
        super().__init__(message)


class GeminiCompatibilityError(SchemaCompatibilityError):
    """Exception raised when a schema is not compatible with Gemini API."""

    def __init__(self, model: type, issues: dict[str, list[str]]):
        self.model = model
        self.issues = issues
        message = f"Gemini API compatibility issues found in {model.__name__}: {issues}"
        super().__init__(message)


class OpenRouterRateLimitError(Exception):
    pass


class OpenRouterTimeOutError(Exception):
    pass


class OpenRouterOverloadedError(Exception):
    pass


class OpenRouterTransientError(Exception):
    """Transient error from OpenRouter that should be retried."""

    pass


# from vision_llm import a_vision_llm__gpt4o


class OpenRouterCapabilities(BaseModel):
    """Capabilities of a model in OpenRouter API."""

    vision: bool = False
    json: bool = False
    tools: bool = False

    model_config = {
        "extra": "allow"  # Allow extra fields for compatibility with changing API
    }


class OpenRouterArchitecture(BaseModel):
    """Architecture information for an OpenRouter model."""

    modality: str
    tokenizer: str
    instruct_type: str | None = None
    input_modalities: list[str] | None = None
    output_modalities: list[str] | None = None
    capabilities: OpenRouterCapabilities | None = None

    model_config = {
        "extra": "allow"  # Allow extra fields for compatibility with changing API
    }


class OpenRouterModelPricing(BaseModel):
    """Pricing information for an OpenRouter model."""

    prompt: str
    completion: str
    image: str | None = None
    request: str | None = None
    web_search: str | None = None
    internal_reasoning: str | None = None
    input_cache_read: str | None = None
    input_cache_write: str | None = None

    model_config = {
        "extra": "allow"  # Allow extra fields for compatibility with changing API
    }

    def calc_cost(self, usage: CompletionUsage):
        completion_cost = usage.completion_tokens * float(self.completion)
        prompt_cost = usage.prompt_tokens * float(self.prompt)
        return dict(
            completion=completion_cost,
            prompt=prompt_cost,
        )

    def calc_cost_dict(self, usage: dict):
        completion_cost = usage["completion_tokens"] * float(self.completion)
        prompt_cost = usage["prompt_tokens"] * float(self.prompt)
        return dict(
            completion=completion_cost,
            prompt=prompt_cost,
        )


class OpenRouterProviderInfo(BaseModel):
    """Provider information for an OpenRouter model."""

    id: str | None = None
    name: str | None = None
    parameters: dict[str, Any] | None = None
    is_moderated: bool = False
    context_length: int | None = None
    max_completion_tokens: int | None = None
    can_stream: bool | None = True

    model_config = {
        "extra": "allow"  # Allow extra fields for compatibility with changing API
    }


class OpenRouterModel(BaseModel):
    """Represents a model in the OpenRouter API."""

    id: str
    name: str
    created: int
    description: str
    context_length: int
    architecture: OpenRouterArchitecture
    pricing: OpenRouterModelPricing
    providers: list[OpenRouterProviderInfo] | None = None
    top_provider: OpenRouterProviderInfo | None = None
    per_request_limits: dict[str, Any] | None = None

    model_config = {
        "extra": "allow"  # Allow extra fields for compatibility with changing API
    }

    def supports_json_output(self) -> bool:
        """Check if the model supports JSON structured output."""
        if self.architecture.capabilities:
            return self.architecture.capabilities.json
        return False


class OpenRouterModelTable(BaseModel):
    """Collection of models available in the OpenRouter API."""

    data: list[OpenRouterModel]

    model_config = {
        "extra": "allow"  # Allow extra fields for compatibility with changing API
    }

    def pricing(self, model_id: str) -> OpenRouterModelPricing:
        if not hasattr(self, "_mut_pricing"):
            self._mut_pricing = {model.id: model.pricing for model in self.data}
        return self._mut_pricing[model_id]

    def safe_pricing(self, model_id: str) -> ResultE[OpenRouterModelPricing]:
        return safe(self.pricing)(model_id)

    def get_model(self, model_id: str) -> OpenRouterModel | None:
        """Get a model by its ID."""
        for model in self.data:
            if model.id == model_id:
                return model
        return None

    def supports_json_output(self, model_id: str) -> bool:
        """Check if a model supports JSON structured output by its ID."""
        model = self.get_model(model_id)
        if model:
            return model.supports_json_output()
        return False


@instance
@retry(
    stop=stop_after_attempt(5),
)
async def openrouter_model_table(logger: Any) -> OpenRouterModelTable:
    async with httpx.AsyncClient() as client:
        response = await client.get("https://openrouter.ai/api/v1/models")
        response.raise_for_status()
        data = response.json()["data"]

        try:
            return OpenRouterModelTable.model_validate(dict(data=data))
        except ValidationError as ve:
            logger.error(
                f"Error in OpenRouterModelTable validation: {ve} caused by: \n{data}"
            )
            raise ve


@instance
def openrouter_api(openrouter_api_key: str):
    return AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1", api_key=openrouter_api_key
    )


@instance
def openrouter_state():
    return dict()


@instance
def openrouter_timeout_sec() -> float:
    return 120


class LoggerProtocol(Protocol):
    """Protocol for logger interface."""

    def info(self, message: str) -> None: ...
    def warning(self, message: str) -> None: ...
    def error(self, message: str) -> None: ...
    def success(self, message: str) -> None: ...


class AOpenrouterPostProtocol(Protocol):
    async def __call__(self, payload: dict) -> dict: ...


@injected(protocol=AOpenrouterPostProtocol)
async def a_openrouter_post(
    openrouter_api_key: str,
    openrouter_timeout_sec: float,
    logger: LoggerProtocol,
    /,
    payload: dict,
) -> dict:
    async with httpx.AsyncClient() as client:
        headers = {
            "Authorization": f"Bearer {openrouter_api_key}",
            "Content-Type": "application/json",
        }
        response = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=openrouter_timeout_sec,
        )

        # Check if response is JSON before parsing
        content_type = response.headers.get("content-type", "")
        if "application/json" not in content_type.lower():
            # Log the actual response for debugging
            logger.error(
                f"Non-JSON response from OpenRouter. Status: {response.status_code}, Content-Type: {content_type}"
            )
            logger.error(f"Response body: {response.text[:500]}...")  # First 500 chars

            # Check for common error status codes
            if response.status_code == 502:
                raise OpenRouterOverloadedError(
                    {
                        "error": {
                            "code": 502,
                            "message": "Bad Gateway - Server overloaded",
                        }
                    }
                )
            elif response.status_code == 503:
                raise OpenRouterTransientError(
                    {
                        "error": {
                            "code": 503,
                            "message": "Service temporarily unavailable",
                        }
                    }
                )
            elif response.status_code == 504:
                raise OpenRouterTimeOutError(
                    {"error": {"code": 504, "message": "Gateway timeout"}}
                )
            elif response.status_code >= 500:
                raise OpenRouterTransientError(
                    {
                        "error": {
                            "code": response.status_code,
                            "message": f"Server error: {response.text[:200]}",
                        }
                    }
                )
            else:
                raise RuntimeError(
                    f"Non-JSON response from OpenRouter (status {response.status_code}): {response.text[:500]}"
                )

        # Try to parse JSON, handle errors gracefully
        try:
            return response.json()
        except Exception as e:
            logger.error(
                f"Failed to parse JSON response. Status: {response.status_code}"
            )
            logger.error(f"Response body: {response.text[:500]}...")

            # If it's a 5xx error, treat as transient
            if response.status_code >= 500:
                raise OpenRouterTransientError(
                    {
                        "error": {
                            "code": response.status_code,
                            "message": f"Server error with invalid JSON: {e!s}",
                        }
                    }
                )
            else:
                raise RuntimeError(
                    f"Invalid JSON response from OpenRouter: {e!s}. Response: {response.text[:500]}"
                )


class OpenRouterAPIProtocol(Protocol):
    """Protocol for OpenRouter API client."""

    def __init__(self, base_url: str, api_key: str) -> None: ...


class SimpleLlmProtocol(Protocol):
    async def __call__(self, prompt: str) -> Any: ...


class ACachedSchemaExampleProviderProtocol(Protocol):
    async def __call__(self, model_schema: dict) -> Any: ...


@async_cached(sqlite_dict(injected("cache_root_path") / "schema_examples.sqlite"))
@injected(protocol=ACachedSchemaExampleProviderProtocol)
async def a_cached_schema_example_provider(
    a_llm_for_json_schema_example: SimpleLlmProtocol, /, model_schema: dict
) -> Any:
    prompt = f"""
    Provide example json objects that follows the schema of the model:{model_schema}
    Beware the example must not be in yaml format.
    If the model contains a list property, provide an example of a case where the list is empty and another example where the list contains multiple items.
    Beware that `type` field is required in the schema, so make sure to include it in the example.
    """
    return await a_llm_for_json_schema_example(prompt)


class OpenRouterChatCompletion(Protocol):
    async def __call__(
        self,
        prompt: str,
        model: str,
        max_tokens: int = 8192,
        temperature: float = 1,
        images: list[PIL.Image.Image] | None = None,
        response_format: BaseModel | None = None,
        provider: dict[str, Any] | None = None,
        **kwargs,
    ) -> Any: ...


class AOpenrouterChatCompletionWithoutFixProtocol(Protocol):
    async def __call__(
        self,
        prompt: str,
        model: str,
        max_tokens: int = 8192,
        temperature: float = 1,
        images: list[PIL.Image.Image] | None = None,
        response_format=None,
        provider: dict | None = None,
        include_reasoning: bool = False,
        reasoning: dict | None = None,
        **kwargs,
    ) -> Any: ...


@injected(protocol=AOpenrouterChatCompletionWithoutFixProtocol)
@retry(
    retry=retry_if_exception_type(
        (
            httpx.ReadTimeout,
            OpenRouterRateLimitError,
            OpenRouterOverloadedError,
            OpenRouterTransientError,
        )
    ),
    stop=stop_after_attempt(10),
    wait=wait_exponential(multiplier=1, min=5, max=120),
)
async def a_openrouter_chat_completion__without_fix(  # noqa: PINJ045
    a_openrouter_post: AOpenrouterPostProtocol,
    logger: LoggerProtocol,
    openrouter_model_table: OpenRouterModelTable,
    openrouter_state: dict,
    /,
    prompt: str,
    model: str,
    max_tokens: int = 8192,
    temperature: float = 1,
    images: list[PIL.Image.Image] | None = None,
    response_format=None,
    provider: dict | None = None,
    include_reasoning: bool = False,
    reasoning: dict | None = None,
    **kwargs,
) -> Any:
    """
    :param prompt:
    :param model:
    :param max_tokens:
    :param temperature:
    :param images:
    :param response_format:
    :param provider:  see:https://openrouter.ai/docs/features/provider-routing
    Example:
    provider={'order': [
        'openai',
        'together'
      ],
      allow_fallbacks=False # if everything in order fails, fails the completion. Default is True so some other provider will be used.
    }
    :param include_reasoning: Whether to include reasoning tokens in the response
    :param reasoning: Advanced reasoning configuration dict with keys:
        - effort: 'high', 'medium', or 'low' (controls reasoning allocation)
        - max_tokens: specific token limit for reasoning
        - exclude: whether to exclude reasoning from response
        - enabled: whether reasoning is enabled
    :param kwargs:
    :return:
    """

    provider_filter = dict()
    if response_format is not None and issubclass(response_format, BaseModel):
        provider_filter["provider"] = {"require_parameters": True}
        openai_response_format = build_openrouter_response_format(response_format)
        provider_filter["response_format"] = openai_response_format
    elif response_format is not None:
        provider_filter["response_format"] = response_format

    if provider is not None:
        p = provider_filter.get("provider", dict())
        p.update(provider)
        provider_filter["provider"] = p

    # Build payload (simple version without resizing)
    images = images or []
    payload: dict[str, Any] = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    *[to_content(img) for img in images],
                ],
            }
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
        **provider_filter,
        **kwargs,
    }

    # Add reasoning support
    if include_reasoning:
        payload["include_reasoning"] = True

    if reasoning is not None:
        payload["reasoning"] = reasoning

    # Make API call
    res = await a_openrouter_post(payload)
    handle_openrouter_error(res, logger)

    # Track costs
    cost_dict: ResultE[dict] = openrouter_model_table.safe_pricing(model).bind(
        safe(lambda x: x.calc_cost_dict(res["usage"]))
    )
    # Don't mutate state, just log the cost
    current_cost = openrouter_state.get("cumulative_cost", 0)
    new_cost = current_cost + sum(cost_dict.value_or(dict()).values())

    logger.info(
        f"Cost of completion: {cost_dict.value_or('unknown')}, cumulative cost: {new_cost} from {res['provider']}"
    )

    # Extract response content
    data = res["choices"][0]["message"]["content"]

    # Handle structured response format
    if response_format is not None and issubclass(response_format, BaseModel):
        # Simple parsing without LLM fix
        try:
            json_data = extract_json_from_markdown(data)
            return response_format.model_validate_json(json_data)
        except Exception as e:
            logger.warning(
                f"Error in response validation:\n{pformat(payload)}\n{pformat(res)} \n {e} cause:\n{data}"
            )
            data_dict = json_repair.loads(data)
            return response_format.model_validate(data_dict)
    else:
        return data


def handle_openrouter_error(res: dict, logger: LoggerProtocol):
    """Handle error responses from OpenRouter API."""

    if "error" not in res:
        return

    error = res.get("error", {})
    error_code = error.get("code")
    error_msg = str(res)

    # Rate limit errors
    if error_code == 429 or "Rate limit" in error_msg or "rate-limited" in error_msg:
        logger.warning(f"Rate limit error in response: {pformat(res)}")
        raise OpenRouterRateLimitError(res)

    # Timeout errors
    if "Timed out" in error_msg:
        logger.warning(f"Timed out error in response: {pformat(res)}")
        raise OpenRouterTimeOutError(res)

    # Overloaded errors
    if "Overloaded" in error_msg or error_code == 502:
        logger.warning(f"Overloaded error in response: {pformat(res)}")
        raise OpenRouterOverloadedError(res)

    # Transient errors that should be retried
    transient_codes = {520, 503, 522, 524}
    if error_code in transient_codes:
        logger.warning(f"Transient error (code {error_code}): {pformat(res)}")
        raise OpenRouterTransientError(res)

    # Provider errors that might be transient
    if error_code == 520 and "Provider returned error" in error_msg:
        logger.warning(f"Provider transient error: {pformat(res)}")
        raise OpenRouterTransientError(res)

    raise RuntimeError(f"Error in response: {pformat(res)}")


def extract_json_from_markdown(data: str) -> str:
    """Extract JSON from markdown code blocks."""
    if "```" in data:
        return data.split("```")[1].strip()
    return data


async def parse_json_response(
    data: str,
    response_format: type[BaseModel],
    logger,
    a_structured_llm_for_json_fix=None,
    prompt: str | None = None,
) -> Any:
    """Parse and validate JSON response with fallback repair mechanisms."""

    # Try direct parsing
    try:
        json_data = extract_json_from_markdown(data)
        return response_format.model_validate_json(json_data)
    except Exception as e:
        logger.warning(f"Error in response validation: {e}")

        # Try json_repair
        try:
            data_dict = json_repair.loads(data)
            return response_format.model_validate(data_dict)
        except Exception:
            logger.warning(f"json_repair could not repair: {data}")

            # Use LLM fix if available
            if a_structured_llm_for_json_fix and prompt:
                fix_prompt = f"""
An LLM failed to answer the following input with a correct json format.
Please fix the following json object (Response) to match the schema:
# Original Input:
{prompt}
# Response
{data}
"""
                return await a_structured_llm_for_json_fix(
                    fix_prompt, response_format=response_format
                )
            raise


def calculate_cumulative_cost(openrouter_state: dict, cost_dict: ResultE[dict]) -> dict:
    """Calculate new state with updated cumulative cost."""
    new_cost = openrouter_state.get("cumulative_cost", 0) + sum(
        cost_dict.value_or(dict()).values()
    )
    return {**openrouter_state, "cumulative_cost": new_cost}


class AResizeImageBelow5mbProtocol(Protocol):
    async def __call__(self, img: PIL.Image.Image) -> PIL.Image.Image: ...


# Helper class removed - replaced with composed @injected functions below


# Factory function removed - functionality moved to a_openrouter_chat_completion


def build_openrouter_response_format(response_format):
    pydantic_schema = response_format.model_json_schema()
    match pydantic_schema:
        case {"$defs": defs}:
            for k, d in defs.items():
                d["additionalProperties"] = False
    pydantic_schema["additionalProperties"] = False
    schema_dict = dict(
        name=response_format.__name__,
        description=f"Pydantic model for {response_format}",
        strict=True,
        schema=pydantic_schema,
    )
    openai_response_format = dict(
        type="json_schema",
        json_schema=schema_dict,
    )
    return openai_response_format


@injected(protocol=AResizeImageBelow5mbProtocol)
async def a_resize_image_below_5mb(logger: LoggerProtocol, /, img: PIL.Image.Image):
    """
    画像を5MB以下にリサイズします。
    元の画像のアスペクト比を保持しながら、必要に応じて徐々に縮小します。

    Args:
        logger: ロガーオブジェクト
        img (PIL.Image.Image): リサイズする画像

    Returns:
        PIL.Image.Image: 5MB以下にリサイズされた画像
    """
    import io

    def get_image_size_mb(image: PIL.Image.Image) -> float:
        buffer = io.BytesIO()
        image.save(buffer, format=image.format or "PNG")
        return buffer.tell() / (1024 * 1024)  # バイト数をMBに変換

    current_img = img.copy()
    current_size_mb = get_image_size_mb(current_img)

    if current_size_mb <= 5:
        return current_img

    logger.info(
        f"画像サイズが5MBを超えています。縮小を開始します。（現在: {current_size_mb:.2f}MB, 解像度: {current_img.size}）"
    )
    resize_count = 0
    while current_size_mb > 5:
        # 現在のサイズを取得
        width, height = current_img.size
        # 10%ずつ縮小
        new_width = int(width * 0.9)
        new_height = int(height * 0.9)
        # リサイズ実行
        current_img = current_img.resize(
            (new_width, new_height), PIL.Image.Resampling.LANCZOS
        )
        current_size_mb = get_image_size_mb(current_img)
        resize_count += 1

        if resize_count % 5 == 0:  # 5回ごとにログを出力
            logger.info(f"縮小中: {current_size_mb:.2f}MB, 解像度: {current_img.size}")

    logger.success(
        f"縮小完了: {current_size_mb:.2f}MB, 最終解像度: {current_img.size}（{resize_count}回の縮小）"
    )
    return current_img


__openapi3_compatibility_cache = {}


def is_openapi3_compatible(model: type[BaseModel]) -> dict[str, list[str]]:
    """
    Pydantic BaseModelがOpenAPI 3.0と互換性があるかどうかを判別し、
    問題がある場合はその詳細を返します。

    Args:
        model: チェックするPydantic BaseModelクラス

    Returns:
        互換性の問題のリスト（キー: フィールド名、値: 問題の説明）
        空の辞書が返される場合は、問題が見つからなかったことを意味します
    """
    if model in __openapi3_compatibility_cache:
        return __openapi3_compatibility_cache[model]
    incompatibilities = {}

    # モデルのフィールドを取得
    fields = model.__annotations__

    for field_name, field_type in fields.items():
        issues = []

        # Union型の検出 (Optional[X]はUnion[X, None]として扱われる)
        if get_origin(field_type) is Union:
            # Optional[X] (Union[X, None])は一般的にサポートされているが、
            # 複数の型を含むUnionはOpenAPI 3.0ではサポートされていない
            args = get_args(field_type)
            if len(args) > 2 or (len(args) == 2 and type(None) not in args):
                issues.append(
                    f"複数タイプのUnion型はOpenAPI 3.0でサポートされていません: {field_type}"
                )

        # List[Union[...]]のような入れ子になった複雑な型をチェック
        if get_origin(field_type) in (list, list) and get_args(field_type):
            inner_type = get_args(field_type)[0]
            if get_origin(inner_type) is Union and len(get_args(inner_type)) > 2:
                issues.append(
                    f"リスト内の複数Unionタイプ {inner_type} はOpenAPI 3.0でサポートされていません"
                )

        # 再帰的な型参照のチェック（自己参照など）
        if inspect.isclass(field_type) and issubclass(field_type, BaseModel):
            # 自己参照型をチェック（簡易版）
            if field_type == model:
                issues.append(
                    "自己参照モデルはOpenAPI 3.0で問題を引き起こす可能性があります"
                )

            # 入れ子になったモデルを再帰的にチェック
            nested_issues = is_openapi3_compatible(field_type)
            if nested_issues:
                for nested_field, nested_issue_list in nested_issues.items():
                    issues.extend(
                        [
                            f"入れ子モデルの問題 ({nested_field}): {issue}"
                            for issue in nested_issue_list
                        ]
                    )

        # Literal型のチェック
        try:
            from typing import Literal

            if get_origin(field_type) is Literal:
                # Literalタイプはスキーマで'enum'として表示されますが、
                # 値の型がすべて同じである必要があります
                literal_args = get_args(field_type)
                arg_types = set(type(arg) for arg in literal_args)
                if len(arg_types) > 1:
                    issues.append(
                        f"異なる型のLiteral値はOpenAPI 3.0でサポートされていません: {field_type}"
                    )
        except ImportError:
            pass  # Python 3.7以前ではLiteralが使用できない

        # DiscriminatedUnionのチェック
        if hasattr(model, "model_config") and getattr(
            model.model_config, "json_schema_extra", None
        ):
            extra = model.model_config.json_schema_extra
            if isinstance(extra, dict) and "discriminator" in extra:
                issues.append(
                    "discriminatorはOpenAPI 3.0の実装によっては完全にサポートされていない場合があります"
                )

        if issues:
            incompatibilities[field_name] = issues

    __openapi3_compatibility_cache[model] = incompatibilities

    return incompatibilities


__gemini_compatibility_cache = {}


def is_gemini_compatible(model: type[BaseModel]) -> dict[str, list[str]]:
    """
    Pydantic BaseModelがGoogle Gemini APIと互換性があるかどうかを判別し、
    問題がある場合はその詳細を返します。Gemini APIはOpenAPI 3.0のサブセットのみをサポートしており、
    特定の型と構造のみをサポートします。

    サポートされる型:
    - string (format: enum, datetime)
    - integer (format: int32, int64)
    - number (format: float, double)
    - bool
    - array (items, minItems, maxItems)
    - object (properties, required, propertyOrdering, nullable)

    Args:
        model: チェックするPydantic BaseModelクラス

    Returns:
        互換性の問題のリスト（キー: フィールド名、値: 問題の説明）
        空の辞書が返される場合は、問題が見つからなかったことを意味します
    """
    if model in __gemini_compatibility_cache:
        return __gemini_compatibility_cache[model]

    incompatibilities = {}

    # モデルのフィールドを取得
    fields = model.__annotations__

    for field_name, field_type in fields.items():
        issues = []

        # Unionはサポートされていない (Optional含む)
        if get_origin(field_type) is Union:
            args = get_args(field_type)
            if type(None) in args:
                issues.append(
                    f"Optional型はGemini APIではサポートされていません。代わりに nullable フラグを使用する必要があります: {field_type}"
                )
            else:
                issues.append(
                    f"Union型はGemini APIではサポートされていません: {field_type}"
                )

        # リスト/配列の検証
        elif get_origin(field_type) in (list, list) and get_args(field_type):
            inner_type = get_args(field_type)[0]

            # リスト内のUnion型はサポートされていない
            if get_origin(inner_type) is Union:
                issues.append(
                    f"リスト内のUnion型はGemini APIではサポートされていません: List[{inner_type}]"
                )

            # リスト内の要素が複雑なオブジェクトの場合、再帰的に検証
            if inspect.isclass(inner_type) and issubclass(inner_type, BaseModel):
                nested_issues = is_gemini_compatible(inner_type)
                if nested_issues:
                    issues.append(
                        f"リスト内の要素に互換性の問題があります: List[{inner_type}]"
                    )

        # 辞書型の検証
        elif get_origin(field_type) in (dict, dict):
            # 辞書型のキー・バリューの型を取得
            key_type, value_type = get_args(field_type)

            # キーがstr型でない場合は警告
            if key_type is not str:
                issues.append(
                    f"Gemini APIで辞書型を使用する場合、キーはstr型である必要があります: Dict[{key_type}, {value_type}]"
                )

            # 値が複合型の場合は再帰的に検証
            if get_origin(value_type) is not None:
                issues.append(
                    f"Gemini APIで辞書型の値に複合型を使用することは推奨されません: Dict[{key_type}, {value_type}]"
                )
            elif inspect.isclass(value_type) and issubclass(value_type, BaseModel):
                nested_issues = is_gemini_compatible(value_type)
                if nested_issues:
                    issues.append(
                        f"辞書型の値に互換性の問題があるモデルが使用されています: Dict[{key_type}, {value_type}]"
                    )

        # Literalのチェック - Geminiではenumとして扱われる
        elif get_origin(field_type) is Literal:
            literal_args = get_args(field_type)
            arg_types = set(type(arg) for arg in literal_args)
            if len(arg_types) > 1:
                issues.append(
                    f"異なる型を含むLiteral値はGemini APIではサポートされていません。すべての値は同じ型である必要があります: {field_type}"
                )

        # 複雑なオブジェクト (BaseModel) の場合、再帰的に検証
        elif inspect.isclass(field_type) and issubclass(field_type, BaseModel):
            # 自己参照型をチェック
            if field_type == model:
                issues.append("自己参照モデルはGemini APIではサポートされていません")

            # 入れ子になったモデルを再帰的にチェック
            nested_issues = is_gemini_compatible(field_type)
            if nested_issues:
                for nested_field, nested_issue_list in nested_issues.items():
                    issues.extend(
                        [
                            f"入れ子モデルの問題 ({nested_field}): {issue}"
                            for issue in nested_issue_list
                        ]
                    )

        # サポートされていない型のチェック
        else:
            # Python組み込み型との対応関係を確認
            supported_types = {
                str: "string",
                int: "integer",
                float: "number",
                bool: "bool",
                list: "array",
                dict: "object",
            }

            # フィールドの型が直接サポートされているかチェック
            is_supported = False
            for py_type, schema_type in supported_types.items():
                if field_type is py_type:
                    is_supported = True
                    break

            if not is_supported:
                issues.append(
                    f"このフィールドの型 {field_type} はGemini APIではサポートされていない可能性があります。"
                    + "サポートされる型: string, integer, number, bool, array, object"
                )

        if issues:
            incompatibilities[field_name] = issues

    __gemini_compatibility_cache[model] = incompatibilities
    return incompatibilities


class AOpenrouterChatCompletionProtocol(Protocol):
    async def __call__(
        self,
        prompt: str,
        model: str,
        max_tokens: int = 8192,
        temperature: float = 1,
        images: list[PIL.Image.Image] | None = None,
        response_format=None,
        provider: dict | None = None,
        include_reasoning: bool = False,
        reasoning: dict | None = None,
        **kwargs,
    ) -> Any: ...


@injected(protocol=AOpenrouterChatCompletionProtocol)
@retry(
    retry=retry_if_exception_type(
        (
            httpx.ReadTimeout,
            OpenRouterRateLimitError,
            OpenRouterOverloadedError,
            OpenRouterTransientError,
        )
    ),
    stop=stop_after_attempt(10),
    wait=wait_exponential(multiplier=1, min=5, max=120),
)
async def a_openrouter_chat_completion(  # noqa: PINJ045
    openrouter_model_table: OpenRouterModelTable,
    a_cached_schema_example_provider: ACachedSchemaExampleProviderProtocol,
    a_structured_llm_for_json_fix: "StructuredLLM",
    logger: LoggerProtocol,
    a_resize_image_below_5mb: AResizeImageBelow5mbProtocol,
    openrouter_state: dict,
    a_openrouter_post: AOpenrouterPostProtocol,
    /,
    prompt: str,
    model: str,
    max_tokens: int = 8192,
    temperature: float = 1,
    images: list[PIL.Image.Image] | None = None,
    response_format=None,
    provider: dict | None = None,
    include_reasoning: bool = False,
    reasoning: dict | None = None,
    **kwargs,
):
    """
    Chat completion with JSON fixing capability for models that don't support structured output.

    This is the main API endpoint that maintains backward compatibility.
    Mode parameters are allowed here with # noqa for the linter.
    """
    provider_filter = dict()
    use_json_fix_fallback = False

    # Setup response format configuration if provided
    if response_format is not None and issubclass(response_format, BaseModel):
        # Check OpenAPI 3.0 compatibility for all models
        if issues := is_openapi3_compatible(response_format):
            raise OpenAPI3CompatibilityError(response_format, issues)

        # Additional Gemini-specific compatibility check when model contains 'gemini'
        if "gemini" in model.lower() and (
            gemini_issues := is_gemini_compatible(response_format)
        ):
            raise GeminiCompatibilityError(response_format, gemini_issues)

        # Check if model supports JSON
        supports_json = openrouter_model_table.supports_json_output(model)

        # Only add response_format to payload if model supports JSON
        if supports_json:
            provider_filter["provider"] = {"require_parameters": True}
            openai_response_format = build_openrouter_response_format(response_format)
            provider_filter["response_format"] = openai_response_format
        else:
            # Model doesn't support JSON, we'll use JSON fix fallback
            use_json_fix_fallback = True
            logger.warning(
                f"Model {model} does not support JSON output. "
                f"Will use fallback JSON fix mechanism."
            )

        # Always add schema example to prompt for better results
        schema_prompt = await a_cached_schema_example_provider(
            response_format.model_json_schema()
        )
        prompt += f"""\n\nThe response must follow the following json format example:{schema_prompt}"""

    # Update provider filter if provider is specified
    if provider is not None:
        p = provider_filter.get("provider", dict())
        p.update(provider)
        provider_filter["provider"] = p

    # Prepare images
    images = images or []
    images = [await a_resize_image_below_5mb(img) for img in images]

    # Build payload
    payload: dict[str, Any] = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    *[to_content(img) for img in images],
                ],
            }
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
        **provider_filter,
        **kwargs,
    }

    # Add reasoning support
    if include_reasoning:
        payload["include_reasoning"] = True

    if reasoning is not None:
        payload["reasoning"] = reasoning

    # Make API call
    res = await a_openrouter_post(payload)
    handle_openrouter_error(res, logger)

    # Track costs (without mutating state directly)
    cost_dict: ResultE[dict] = openrouter_model_table.safe_pricing(model).bind(
        safe(lambda x: x.calc_cost_dict(res["usage"]))
    )
    current_cost = openrouter_state.get("cumulative_cost", 0)
    new_cost = current_cost + sum(cost_dict.value_or(dict()).values())
    # Note: Not mutating state to avoid PINJ056 - cost tracking happens at higher level

    logger.info(
        f"Cost of completion: {cost_dict.value_or('unknown')}, cumulative cost: {new_cost} from {res['provider']}"
    )

    # Extract response content
    data = res["choices"][0]["message"]["content"]

    # Handle structured response format if provided
    if response_format is not None and issubclass(response_format, BaseModel):
        # If model doesn't support JSON, always use JSON fix
        if use_json_fix_fallback:
            fix_prompt = f"""
Extract and format the following response into the required JSON structure.
# Original Prompt:
{prompt}
# Response
{data}
"""
            return await a_structured_llm_for_json_fix(
                fix_prompt, response_format=response_format
            )

        # Model supports JSON, try to parse normally
        return await parse_json_response(
            data=data,
            response_format=response_format,
            logger=logger,
            a_structured_llm_for_json_fix=a_structured_llm_for_json_fix,
            prompt=prompt,
        )
    else:
        return data


# Removed - functionality merged into a_openrouter_chat_completion


class ALlmOpenrouterProtocol(Protocol):
    async def __call__(
        self,
        text: str,
        model: str,
        response_format=None,
        **kwargs,
    ) -> Any: ...


@injected(protocol=ALlmOpenrouterProtocol)
async def a_llm__openrouter(  # noqa: PINJ045
    openrouter_model_table: OpenRouterModelTable,
    openrouter_api: OpenRouterAPIProtocol,
    a_openai_compatible_llm: AOpenaiCompatibleLlmProtocol,
    logger: LoggerProtocol,
    openrouter_state: dict,
    /,
    text: str,
    model: str,
    response_format=None,
    **kwargs,
):
    # If response_format is provided, check compatibility
    if response_format is not None and issubclass(response_format, BaseModel):
        # Check OpenAPI 3.0 compatibility for all models
        if issues := is_openapi3_compatible(response_format):
            raise OpenAPI3CompatibilityError(response_format, issues)

        # Additional Gemini-specific compatibility check when model contains 'gemini'
        if "gemini" in model.lower() and (
            gemini_issues := is_gemini_compatible(response_format)
        ):
            raise GeminiCompatibilityError(response_format, gemini_issues)

    res: ChatCompletion = await a_openai_compatible_llm(
        api=openrouter_api,
        model=model,
        text=text,
        response_format=response_format,
        **kwargs,
    )

    cost = openrouter_model_table.pricing(model).calc_cost(res.usage)
    total_cost = sum(cost.values())
    # Don't mutate state, just log the cost
    current_cumulative = openrouter_state.get("cumulative_cost", 0)
    new_cumulative = current_cumulative + total_cost
    logger.info(
        f"Cost of completion: {cost}, total cost: {total_cost}, cumulative cost: {new_cumulative}"
    )

    data = res.choices[0].message.content
    if response_format is not None and issubclass(response_format, BaseModel):
        if "```" in data:
            data = data.split("```")[1].strip()
        data = response_format.model_validate_json(data)
    return data


class Text(BaseModel):
    text_lines: list[str]


class OptionalText(BaseModel):
    text_lines: list[str] | None


test_call_gpt4o: IProxy[Any] = a_openrouter_chat_completion__without_fix(
    prompt="What is the capital of Japan?", model="openai/gpt-4o"
)

test_openai_compatible_llm: IProxy[Any] = a_openai_compatible_llm(
    api=openrouter_api,
    model="deepseek/deepseek-chat",
    text="What is the capital of Japan?",
)

test_openrouter_text: IProxy[Any] = a_llm__openrouter(
    "What is the capital of Japan?", "deepseek/deepseek-chat"
)

test_openrouter_structure: IProxy[Any] = a_llm__openrouter(
    f"What is the capital of Japan?.{Text.model_json_schema()}",
    # "deepseek/deepseek-chat",
    "deepseek/deepseek-r1-distill-qwen-32b",
    response_format=Text,
)

test_openrouter_model_table: IProxy[Any] = openrouter_model_table

test_openrouter_chat_completion: IProxy[Any] = a_openrouter_chat_completion(
    prompt="What is the capital of Japan?", model="deepseek/deepseek-chat"
)

test_openrouter_chat_completion_with_structure: IProxy[Any] = (
    a_openrouter_chat_completion(
        prompt="What is the capital of Japan?",
        model="deepseek/deepseek-chat",
        # model="deepseek/deepseek-r1-distill-qwen-32b",
        response_format=Text,
    )
)

# this must raise error though...
test_openrouter_chat_completion_with_structure_optional: IProxy[Any] = (
    a_openrouter_chat_completion(
        prompt="What is the capital of Japan?",
        model="deepseek/deepseek-chat",
        response_format=OptionalText,
    )
)


# Create example models with Union type for testing
class ContactInfoWithUnion(BaseModel):
    type: Literal["email", "phone"]
    value: str


class PersonWithUnion(BaseModel):
    name: str
    age: int
    contact: ContactInfoWithUnion | str  # Union type with complex object and string


# Test Gemini models with incompatible schema features
# These should raise GeminiCompatibilityError with Gemini-specific compatibility issues

# Test with gemini-pro model
test_gemini_pro_with_incompatible_schema: IProxy[Any] = a_openrouter_chat_completion(
    prompt="What is the capital of Japan?",
    model="google/gemini-pro",
    response_format=PersonWithUnion,  # This has Union type which is incompatible with Gemini
)

# Test with gemini-flash model
test_gemini_flash_with_incompatible_schema: IProxy[Any] = a_openrouter_chat_completion(
    prompt="What is the capital of Japan?",
    model="google/gemini-2.0-flash-001",
    response_format=PersonWithUnion,  # This has Union type which is incompatible with Gemini
)


# Test with a compatible schema
class SimpleResponse(BaseModel):
    answer: str
    confidence: float


test_gemini_flash_with_compatible_schema: IProxy[Any] = a_openrouter_chat_completion(
    prompt="What is the capital of Japan? Answer with high confidence.",
    model="google/gemini-2.0-flash-001",
    response_format=SimpleResponse,  # This should be compatible with Gemini
)

test_is_openapi3_compatible: IProxy[Any] = Injected.pure(is_openapi3_compatible).proxy(
    Text
)
test_is_openapi3_compatible_optional: IProxy[Any] = Injected.pure(
    is_openapi3_compatible
).proxy(OptionalText)

# Tests for is_gemini_compatible function
test_is_gemini_compatible: IProxy[Any] = Injected.pure(is_gemini_compatible).proxy(Text)
test_is_gemini_compatible_optional: IProxy[Any] = Injected.pure(
    is_gemini_compatible
).proxy(OptionalText)

test_is_gemini_compatible_union: IProxy[Any] = Injected.pure(
    is_gemini_compatible
).proxy(PersonWithUnion)


# Create example models with Dictionary for testing
class PersonWithDict(BaseModel):
    name: str
    age: int
    attributes: dict[str, str]  # String keys, string values - should be compatible


class PersonWithComplexDict(BaseModel):
    name: str
    age: int
    scores: dict[int, float]  # Int keys - not compatible


class ComplexValue(BaseModel):
    value: str
    description: str


class PersonWithComplexValueDict(BaseModel):
    name: str
    age: int
    details: dict[
        str, ComplexValue
    ]  # String keys, complex values - partially compatible


test_is_gemini_compatible_dict: IProxy[Any] = Injected.pure(is_gemini_compatible).proxy(
    PersonWithDict
)
test_is_gemini_compatible_complex_key_dict: IProxy[Any] = Injected.pure(
    is_gemini_compatible
).proxy(PersonWithComplexDict)
test_is_gemini_compatible_complex_value_dict: IProxy[Any] = Injected.pure(
    is_gemini_compatible
).proxy(PersonWithComplexValueDict)


# Create example model with nested list of complex objects
class Address(BaseModel):
    street: str
    city: str
    zip_code: str


class PersonWithComplexList(BaseModel):
    name: str
    age: int
    addresses: list[Address]


test_is_gemini_compatible_complex_list: IProxy[Any] = Injected.pure(
    is_gemini_compatible
).proxy(PersonWithComplexList)

test_return_empty_item: IProxy[Any] = a_openrouter_chat_completion(
    prompt="Please answer with empty lines.",
    model="deepseek/deepseek-chat",
    response_format=Text,
)

test_resize_image: IProxy[Any] = a_resize_image_below_5mb(
    PIL.Image.new("RGB", (4000, 4000), color="red")
)

# Test cases for JSON support detection
test_model_supports_json: IProxy[Any] = Injected.partial(
    openrouter_model_table.supports_json_output, model_id="openai/gpt-4o"
)

test_model_no_json_support: IProxy[Any] = Injected.partial(
    openrouter_model_table.supports_json_output, model_id="meta-llama/llama-2-70b-chat"
)

# Test completion with model that doesn't support JSON (should use fallback)
test_completion_no_json_support: IProxy[Any] = a_openrouter_chat_completion(
    prompt="What is the capital of Japan? Answer with the city name and country.",
    model="meta-llama/llama-2-70b-chat",  # Model without JSON support
    response_format=SimpleResponse,
)

# Test completion with model that supports JSON
test_completion_with_json_support: IProxy[Any] = a_openrouter_chat_completion(
    prompt="What is the capital of Japan? Answer with the city name and country.",
    model="openai/gpt-4o",  # This model should support JSON
    response_format=SimpleResponse,
)

# Test reasoning tokens with simple prompt
test_reasoning_simple: IProxy[Any] = a_openrouter_chat_completion(
    prompt="What is 2+2? Think step by step.",
    model="deepseek/deepseek-r1",
    include_reasoning=True,
)

# Test reasoning tokens with structured output
test_reasoning_with_structure: IProxy[Any] = a_openrouter_chat_completion(
    prompt="What is the capital of Japan? Think through this step by step.",
    model="deepseek/deepseek-r1",
    response_format=SimpleResponse,
    include_reasoning=True,
)

# Test reasoning with advanced configuration
test_reasoning_advanced: IProxy[Any] = a_openrouter_chat_completion(
    prompt="Explain why the sky is blue. Use detailed reasoning.",
    model="deepseek/deepseek-r1",
    include_reasoning=True,
    reasoning={
        "effort": "high",
    },
)

# Test reasoning with exclude option
test_reasoning_exclude: IProxy[Any] = a_openrouter_chat_completion(
    prompt="What is the meaning of life?",
    model="deepseek/deepseek-r1",
    reasoning={
        "effort": "medium",
        "exclude": True,  # Use reasoning internally but don't include in response
    },
)


@instance
def __debug_design():
    # from openrouter.instances import a_cached_sllm_gpt4o__openrouter
    # from openrouter.instances import a_cached_sllm_gpt4o_mini__openrouter
    from pinjected_openai.openrouter.instances import (
        a_cached_sllm_gpt4o__openrouter,
        a_cached_sllm_gpt4o_mini__openrouter,
    )

    return design(
        a_llm_for_json_schema_example=a_cached_sllm_gpt4o__openrouter,
        a_structured_llm_for_json_fix=a_cached_sllm_gpt4o_mini__openrouter,
    )


__design__ = design(overrides=__debug_design)
