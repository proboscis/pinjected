import inspect
from typing import Any, Dict, List, Optional, Type, Union, get_origin, get_args
from typing import Callable, Awaitable, Protocol, Literal


# Custom exceptions for schema compatibility issues
class SchemaCompatibilityError(Exception):
    """Base exception for schema compatibility issues."""
    pass


class OpenAPI3CompatibilityError(SchemaCompatibilityError):
    """Exception raised when a schema is not compatible with OpenAPI 3.0."""

    def __init__(self, model: Type, issues: Dict[str, List[str]]):
        self.model = model
        self.issues = issues
        message = f"OpenAPI 3.0 compatibility issues found in {model.__name__}: {issues}"
        super().__init__(message)


class GeminiCompatibilityError(SchemaCompatibilityError):
    """Exception raised when a schema is not compatible with Gemini API."""

    def __init__(self, model: Type, issues: Dict[str, List[str]]):
        self.model = model
        self.issues = issues
        message = f"Gemini API compatibility issues found in {model.__name__}: {issues}"
        super().__init__(message)


import PIL
import httpx
import json_repair
from injected_utils.injected_cache_utils import sqlite_dict, async_cached
from openai import AsyncOpenAI
from openai.types import CompletionUsage
from openai.types.chat import ChatCompletion
from pinjected import instance, design, IProxy, injected, Injected
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, retry_if_exception_type, wait_exponential

from pinjected_openai.compatibles import a_openai_compatible_llm
from pinjected_openai.vision_llm import to_content


# from vision_llm import a_vision_llm__gpt4o


class OpenRouterArchitecture(BaseModel):
    modality: str
    tokenizer: str
    instruct_type: Optional[str] = None


class OpenRouterModelPricing(BaseModel):
    prompt: str
    completion: str
    image: str
    request: str

    def calc_cost(self, usage: CompletionUsage):
        completion_cost = usage.completion_tokens * float(self.completion)
        prompt_cost = usage.prompt_tokens * float(self.prompt)
        return dict(
            completion=completion_cost,
            prompt=prompt_cost,
        )

    def calc_cost_dict(self, usage: dict):
        completion_cost = usage['completion_tokens'] * float(self.completion)
        prompt_cost = usage['prompt_tokens'] * float(self.prompt)
        return dict(
            completion=completion_cost,
            prompt=prompt_cost,
        )


class OpenRouterTopProvider(BaseModel):
    context_length: Optional[int] = None
    max_completion_tokens: Optional[int] = None
    is_moderated: bool


class OpenRouterModel(BaseModel):
    id: str
    name: str
    created: int
    description: str
    context_length: int
    architecture: OpenRouterArchitecture
    pricing: OpenRouterModelPricing
    top_provider: Optional[OpenRouterTopProvider] = None
    per_request_limits: Optional[Dict[str, Any]] = None


class OpenRouterModelTable(BaseModel):
    data: List[OpenRouterModel]

    def pricing(self, model_id: str) -> OpenRouterModelPricing:
        if not hasattr(self, "_pricing"):
            self._pricing = {model.id: model.pricing for model in self.data}
        return self._pricing[model_id]


@instance
@retry(
    stop=stop_after_attempt(5),
)
async def openrouter_model_table(logger) -> OpenRouterModelTable:
    async with httpx.AsyncClient() as client:
        response = await client.get("https://openrouter.ai/api/v1/models")
        response.raise_for_status()
        data = response.json()["data"]
        return OpenRouterModelTable.model_validate(dict(data=data))


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


@injected
async def a_openrouter_post(
        openrouter_api_key: str,
        openrouter_timeout_sec: float,
        /,
        payload: dict
) -> dict:
    async with httpx.AsyncClient() as client:
        headers = {
            "Authorization": f"Bearer {openrouter_api_key}",
            'Content-Type': 'application/json',
        }
        response = await client.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload,
                                     timeout=openrouter_timeout_sec)
        return response.json()


@async_cached(sqlite_dict(injected('cache_root_path') / "schema_examples.sqlite"))
@injected
async def a_cached_schema_example_provider(
        a_llm_for_json_schema_example,
        /,
        model_schema: dict
):
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
            images: List[PIL.Image.Image] = None,
            response_format: Optional[BaseModel] = None,
            provider: Optional[Dict[str, Any]] = None,
            **kwargs
    ) -> Any:
        ...


@injected
async def a_openrouter_chat_completion__without_fix(
        a_openrouter_post,
        logger,
        openrouter_model_table: OpenRouterModelTable,
        openrouter_state: dict,
        /,
        prompt: str,
        model: str,
        max_tokens: int = 8192,
        temperature: float = 1,
        images: list[PIL.Image.Image] = None,
        response_format=None,
        provider: dict = None,
        **kwargs
):
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
    :param kwargs:
    :return:
    """
    provider_filter = dict()
    if response_format is not None and issubclass(response_format, BaseModel):
        provider_filter['provider'] = {
            "require_parameters": True
        }
        openai_response_format = build_openrouter_response_format(response_format)
        provider_filter['response_format'] = openai_response_format
    if provider is not None:
        p = provider_filter.get('provider', dict())
        p.update(provider)
        provider_filter['provider'] = p

    payload: Dict[str, Any] = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    # *[{"type": "image", "data": img} for img in images or []]
                    *[to_content(img) for img in images or []]
                ]
            }
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
        **provider_filter,
        **kwargs
    }
    from pprint import pformat
    res = await a_openrouter_post(payload)
    if 'error' in res:
        raise RuntimeError(f"Error in response. \nPayload:{payload}\nResponse:{pformat(res)}")
    cost_dict = openrouter_model_table.pricing(model).calc_cost_dict(res['usage'])
    openrouter_state['cumulative_cost'] = openrouter_state.get('cumulative_cost', 0) + sum(cost_dict.values())

    logger.info(
        f"Cost of completion: {cost_dict}, cumulative cost: {openrouter_state['cumulative_cost']} from {res['provider']}")
    data = res['choices'][0]['message']['content']

    if response_format is not None and issubclass(response_format, BaseModel):
        try:
            if '```' in data:
                data = data.split('```')[1].strip()
            return response_format.model_validate_json(data)
        except Exception as e:
            logger.warning(f"Error in response validation:\n{pformat(payload)}\n{pformat(res)} \n {e} cause:\n{data}")
            data_dict = json_repair.loads(data)
            return response_format.model_validate(data_dict)
    else:
        return data


def build_openrouter_response_format(response_format):
    pydantic_schema = response_format.model_json_schema()
    pydantic_schema['additionalProperties'] = False
    schema_dict = dict(
        name=response_format.__name__,
        description=f"Pydantic model for {response_format}",
        strict=True,
        schema=pydantic_schema
    )
    openai_response_format = dict(
        type='json_schema',
        json_schema=schema_dict
    )
    return openai_response_format


@injected
async def a_resize_image_below_5mb(logger, /, img: PIL.Image.Image):
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
        image.save(buffer, format=image.format or 'PNG')
        return buffer.tell() / (1024 * 1024)  # バイト数をMBに変換

    current_img = img.copy()
    current_size_mb = get_image_size_mb(current_img)

    if current_size_mb <= 5:
        return current_img

    logger.info(
        f"画像サイズが5MBを超えています。縮小を開始します。（現在: {current_size_mb:.2f}MB, 解像度: {current_img.size}）")
    resize_count = 0
    while current_size_mb > 5:
        # 現在のサイズを取得
        width, height = current_img.size
        # 10%ずつ縮小
        new_width = int(width * 0.9)
        new_height = int(height * 0.9)
        # リサイズ実行
        current_img = current_img.resize((new_width, new_height), PIL.Image.Resampling.LANCZOS)
        current_size_mb = get_image_size_mb(current_img)
        resize_count += 1

        if resize_count % 5 == 0:  # 5回ごとにログを出力
            logger.info(f"縮小中: {current_size_mb:.2f}MB, 解像度: {current_img.size}")

    logger.success(f"縮小完了: {current_size_mb:.2f}MB, 最終解像度: {current_img.size}（{resize_count}回の縮小）")
    return current_img


__openapi3_compatibility_cache = {}


def is_openapi3_compatible(model: Type[BaseModel]) -> Dict[str, List[str]]:
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
                issues.append(f"複数タイプのUnion型はOpenAPI 3.0でサポートされていません: {field_type}")

        # List[Union[...]]のような入れ子になった複雑な型をチェック
        if get_origin(field_type) in (list, List) and get_args(field_type):
            inner_type = get_args(field_type)[0]
            if get_origin(inner_type) is Union and len(get_args(inner_type)) > 2:
                issues.append(f"リスト内の複数Unionタイプ {inner_type} はOpenAPI 3.0でサポートされていません")

        # 再帰的な型参照のチェック（自己参照など）
        if inspect.isclass(field_type) and issubclass(field_type, BaseModel):
            # 自己参照型をチェック（簡易版）
            if field_type == model:
                issues.append(f"自己参照モデルはOpenAPI 3.0で問題を引き起こす可能性があります")

            # 入れ子になったモデルを再帰的にチェック
            nested_issues = is_openapi3_compatible(field_type)
            if nested_issues:
                for nested_field, nested_issue_list in nested_issues.items():
                    issues.extend([f"入れ子モデルの問題 ({nested_field}): {issue}" for issue in nested_issue_list])

        # Literal型のチェック
        try:
            from typing import Literal
            if get_origin(field_type) is Literal:
                # Literalタイプはスキーマで'enum'として表示されますが、
                # 値の型がすべて同じである必要があります
                literal_args = get_args(field_type)
                arg_types = set(type(arg) for arg in literal_args)
                if len(arg_types) > 1:
                    issues.append(f"異なる型のLiteral値はOpenAPI 3.0でサポートされていません: {field_type}")
        except ImportError:
            pass  # Python 3.7以前ではLiteralが使用できない

        # DiscriminatedUnionのチェック
        if hasattr(model, 'model_config') and getattr(model.model_config, 'json_schema_extra', None):
            extra = model.model_config.json_schema_extra
            if isinstance(extra, dict) and 'discriminator' in extra:
                issues.append(f"discriminatorはOpenAPI 3.0の実装によっては完全にサポートされていない場合があります")

        if issues:
            incompatibilities[field_name] = issues

    __openapi3_compatibility_cache[model] = incompatibilities

    return incompatibilities


__gemini_compatibility_cache = {}


def is_gemini_compatible(model: Type[BaseModel]) -> Dict[str, List[str]]:
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
                    f"Optional型はGemini APIではサポートされていません。代わりに nullable フラグを使用する必要があります: {field_type}")
            else:
                issues.append(f"Union型はGemini APIではサポートされていません: {field_type}")

        # リスト/配列の検証
        elif get_origin(field_type) in (list, List) and get_args(field_type):
            inner_type = get_args(field_type)[0]

            # リスト内のUnion型はサポートされていない
            if get_origin(inner_type) is Union:
                issues.append(f"リスト内のUnion型はGemini APIではサポートされていません: List[{inner_type}]")

            # リスト内の要素が複雑なオブジェクトの場合、再帰的に検証
            if inspect.isclass(inner_type) and issubclass(inner_type, BaseModel):
                nested_issues = is_gemini_compatible(inner_type)
                if nested_issues:
                    issues.append(f"リスト内の要素に互換性の問題があります: List[{inner_type}]")

        # 辞書型の検証
        elif get_origin(field_type) in (dict, Dict):
            # 辞書型のキー・バリューの型を取得
            key_type, value_type = get_args(field_type)

            # キーがstr型でない場合は警告
            if key_type is not str:
                issues.append(
                    f"Gemini APIで辞書型を使用する場合、キーはstr型である必要があります: Dict[{key_type}, {value_type}]")

            # 値が複合型の場合は再帰的に検証
            if get_origin(value_type) is not None:
                issues.append(
                    f"Gemini APIで辞書型の値に複合型を使用することは推奨されません: Dict[{key_type}, {value_type}]")
            elif inspect.isclass(value_type) and issubclass(value_type, BaseModel):
                nested_issues = is_gemini_compatible(value_type)
                if nested_issues:
                    issues.append(
                        f"辞書型の値に互換性の問題があるモデルが使用されています: Dict[{key_type}, {value_type}]")

        # Literalのチェック - Geminiではenumとして扱われる
        elif get_origin(field_type) is Literal:
            literal_args = get_args(field_type)
            arg_types = set(type(arg) for arg in literal_args)
            if len(arg_types) > 1:
                issues.append(
                    f"異なる型を含むLiteral値はGemini APIではサポートされていません。すべての値は同じ型である必要があります: {field_type}")

        # 複雑なオブジェクト (BaseModel) の場合、再帰的に検証
        elif inspect.isclass(field_type) and issubclass(field_type, BaseModel):
            # 自己参照型をチェック
            if field_type == model:
                issues.append(f"自己参照モデルはGemini APIではサポートされていません")

            # 入れ子になったモデルを再帰的にチェック
            nested_issues = is_gemini_compatible(field_type)
            if nested_issues:
                for nested_field, nested_issue_list in nested_issues.items():
                    issues.extend([f"入れ子モデルの問題 ({nested_field}): {issue}" for issue in nested_issue_list])

        # サポートされていない型のチェック
        else:
            # Python組み込み型との対応関係を確認
            supported_types = {
                str: "string",
                int: "integer",
                float: "number",
                bool: "bool",
                list: "array",
                dict: "object"
            }

            # フィールドの型が直接サポートされているかチェック
            is_supported = False
            for py_type, schema_type in supported_types.items():
                if field_type is py_type:
                    is_supported = True
                    break

            if not is_supported:
                issues.append(f"このフィールドの型 {field_type} はGemini APIではサポートされていない可能性があります。" +
                              "サポートされる型: string, integer, number, bool, array, object")

        if issues:
            incompatibilities[field_name] = issues

    __gemini_compatibility_cache[model] = incompatibilities
    return incompatibilities


@injected
@retry(
    retry=retry_if_exception_type(httpx.ReadTimeout),
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=4, max=10),
)
async def a_openrouter_chat_completion(
        a_openrouter_post,
        logger,
        a_cached_schema_example_provider: Callable[[type], Awaitable[str]],
        a_resize_image_below_5mb,
        a_structured_llm_for_json_fix,
        openrouter_model_table: OpenRouterModelTable,
        openrouter_state: dict,
        /,
        prompt: str,
        model: str,
        max_tokens: int = 8192,
        temperature: float = 1,
        images: list[PIL.Image.Image] = None,
        response_format=None,
        provider: dict = None,
        **kwargs
):
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
    :param kwargs:
    :return:
    """
    provider_filter = dict()
    if response_format is not None and issubclass(response_format, BaseModel):
        # Check OpenAPI 3.0 compatibility for all models
        if issues := is_openapi3_compatible(response_format):
            raise OpenAPI3CompatibilityError(response_format, issues)

        # Additional Gemini-specific compatibility check when model contains 'gemini'
        if 'gemini' in model.lower():
            if gemini_issues := is_gemini_compatible(response_format):
                raise GeminiCompatibilityError(response_format, gemini_issues)

        provider_filter['provider'] = {
            "require_parameters": True
        }
        openai_response_format = build_openrouter_response_format(response_format)
        provider_filter['response_format'] = openai_response_format
        schema_prompt = await a_cached_schema_example_provider(response_format.model_json_schema())
        prompt += f"""The response must follow the following json format example:{schema_prompt}"""
    if provider is not None:
        p = provider_filter.get('provider', dict())
        p.update(provider)
        provider_filter['provider'] = p
    images = images or []

    images = [await a_resize_image_below_5mb(img) for img in images]

    payload: Dict[str, Any] = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    # *[{"type": "image", "data": img} for img in images or []]
                    *[to_content(img) for img in images or []]
                ]
            }
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
        **provider_filter,
        **kwargs
    }
    from pprint import pformat
    # logger.debug(f"payload:{pformat(payload)}")
    res = await a_openrouter_post(payload)
    if 'error' in res:
        raise RuntimeError(f"Error in response: {pformat(res)}")
    cost_dict = openrouter_model_table.pricing(model).calc_cost_dict(res['usage'])
    openrouter_state['cumulative_cost'] = openrouter_state.get('cumulative_cost', 0) + sum(cost_dict.values())
    # logger.debug(f"response:{pformat(res)}")

    logger.info(
        f"Cost of completion: {cost_dict}, cumulative cost: {openrouter_state['cumulative_cost']} from {res['provider']}")
    data = res['choices'][0]['message']['content']

    if response_format is not None and issubclass(response_format, BaseModel):
        try:
            if '```' in data:
                data = data.split('```')[1].strip()
            return response_format.model_validate_json(data)
        except Exception as e:
            logger.warning(f"Error in response validation:\n{pformat(payload)}\n{pformat(res)} \n {e} cause:\n{data}")
            try:
                data_dict = json_repair.loads(data)
                return response_format.model_validate(data_dict)
            except Exception as e:
                logger.warning(f"json_repair could not repair.{data}")
                fix_prompt = f"""
An LLM failed to answer the following input with a correct json format.
Please fix the following json object (Response) to match the schema:
# Original Input:
{prompt}
# Response
{data}
"""
                return await a_structured_llm_for_json_fix(fix_prompt, response_format=response_format)
    else:
        return data


@injected
async def a_llm__openrouter(
        openrouter_model_table: OpenRouterModelTable,
        openrouter_api,
        a_openai_compatible_llm,
        logger,
        openrouter_state: dict,
        /,
        text: str,
        model: str,
        response_format=None,
        **kwargs
):
    # If response_format is provided, check compatibility
    if response_format is not None and issubclass(response_format, BaseModel):
        # Check OpenAPI 3.0 compatibility for all models
        if issues := is_openapi3_compatible(response_format):
            raise OpenAPI3CompatibilityError(response_format, issues)

        # Additional Gemini-specific compatibility check when model contains 'gemini'
        if 'gemini' in model.lower():
            if gemini_issues := is_gemini_compatible(response_format):
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
    openrouter_state['cumulative_cost'] = openrouter_state.get('cumulative_cost', 0) + total_cost
    logger.info(
        f"Cost of completion: {cost}, total cost: {total_cost}, cumulative cost: {openrouter_state['cumulative_cost']}")

    data = res.choices[0].message.content
    if response_format is not None and issubclass(response_format, BaseModel):
        if '```' in data:
            data = data.split('```')[1].strip()
        data = response_format.model_validate_json(data)
    return data


class Text(BaseModel):
    text_lines: list[str]


class OptionalText(BaseModel):
    text_lines: Optional[list[str]]


test_call_gpt4o: IProxy = a_openrouter_chat_completion__without_fix(
    prompt="What is the capital of Japan?",
    model="openai/gpt-4o"
)

test_openai_compatible_llm: IProxy = a_openai_compatible_llm(
    api=openrouter_api,
    model="deepseek/deepseek-chat",
    text="What is the capital of Japan?",
)

test_openrouter_text: IProxy = a_llm__openrouter(
    "What is the capital of Japan?",
    "deepseek/deepseek-chat"
)

test_openrouter_structure: IProxy = a_llm__openrouter(
    f"What is the capital of Japan?.{Text.model_json_schema()}",
    # "deepseek/deepseek-chat",
    "deepseek/deepseek-r1-distill-qwen-32b",
    response_format=Text
)

test_openrouter_model_table: IProxy = openrouter_model_table

test_openrouter_chat_completion: IProxy = a_openrouter_chat_completion(
    prompt="What is the capital of Japan?",
    model="deepseek/deepseek-chat"
)

test_openrouter_chat_completion_with_structure: IProxy = a_openrouter_chat_completion(
    prompt=f"What is the capital of Japan?",
    model="deepseek/deepseek-chat",
    # model="deepseek/deepseek-r1-distill-qwen-32b",
    response_format=Text
)

# this must raise error though...
test_openrouter_chat_completion_with_structure_optional: IProxy = a_openrouter_chat_completion(
    prompt=f"What is the capital of Japan?",
    model="deepseek/deepseek-chat",
    response_format=OptionalText
)


# Create example models with Union type for testing
class ContactInfoWithUnion(BaseModel):
    type: Literal["email", "phone"]
    value: str


class PersonWithUnion(BaseModel):
    name: str
    age: int
    contact: Union[ContactInfoWithUnion, str]  # Union type with complex object and string


# Test Gemini models with incompatible schema features
# These should raise GeminiCompatibilityError with Gemini-specific compatibility issues

# Test with gemini-pro model
test_gemini_pro_with_incompatible_schema: IProxy = a_openrouter_chat_completion(
    prompt=f"What is the capital of Japan?",
    model="google/gemini-pro",
    response_format=PersonWithUnion  # This has Union type which is incompatible with Gemini
)

# Test with gemini-flash model
test_gemini_flash_with_incompatible_schema: IProxy = a_openrouter_chat_completion(
    prompt=f"What is the capital of Japan?",
    model="google/gemini-2.0-flash-001",
    response_format=PersonWithUnion  # This has Union type which is incompatible with Gemini
)

# Test with a compatible schema
class SimpleResponse(BaseModel):
    answer: str
    confidence: float

test_gemini_flash_with_compatible_schema: IProxy = a_openrouter_chat_completion(
    prompt=f"What is the capital of Japan? Answer with high confidence.",
    model="google/gemini-2.0-flash-001",
    response_format=SimpleResponse  # This should be compatible with Gemini
)

test_is_openapi3_compatible: IProxy = Injected.pure(is_openapi3_compatible).proxy(Text)
test_is_openapi3_compatible_optional: IProxy = Injected.pure(is_openapi3_compatible).proxy(OptionalText)

# Tests for is_gemini_compatible function
test_is_gemini_compatible: IProxy = Injected.pure(is_gemini_compatible).proxy(Text)
test_is_gemini_compatible_optional: IProxy = Injected.pure(is_gemini_compatible).proxy(OptionalText)

test_is_gemini_compatible_union: IProxy = Injected.pure(is_gemini_compatible).proxy(PersonWithUnion)


# Create example models with Dictionary for testing
class PersonWithDict(BaseModel):
    name: str
    age: int
    attributes: Dict[str, str]  # String keys, string values - should be compatible


class PersonWithComplexDict(BaseModel):
    name: str
    age: int
    scores: Dict[int, float]  # Int keys - not compatible


class ComplexValue(BaseModel):
    value: str
    description: str


class PersonWithComplexValueDict(BaseModel):
    name: str
    age: int
    details: Dict[str, ComplexValue]  # String keys, complex values - partially compatible


test_is_gemini_compatible_dict: IProxy = Injected.pure(is_gemini_compatible).proxy(PersonWithDict)
test_is_gemini_compatible_complex_key_dict: IProxy = Injected.pure(is_gemini_compatible).proxy(PersonWithComplexDict)
test_is_gemini_compatible_complex_value_dict: IProxy = Injected.pure(is_gemini_compatible).proxy(
    PersonWithComplexValueDict)


# Create example model with nested list of complex objects
class Address(BaseModel):
    street: str
    city: str
    zip_code: str


class PersonWithComplexList(BaseModel):
    name: str
    age: int
    addresses: List[Address]


test_is_gemini_compatible_complex_list: IProxy = Injected.pure(is_gemini_compatible).proxy(PersonWithComplexList)

test_return_empty_item: IProxy = a_openrouter_chat_completion(
    prompt=f"Please answer with empty lines.",
    model="deepseek/deepseek-chat",
    response_format=Text
)

test_resize_image: IProxy = a_resize_image_below_5mb(
    PIL.Image.new('RGB', (4000, 4000), color='red')
)


@instance
def __debug_design():
    from openrouter.instances import a_cached_sllm_gpt4o__openrouter
    from openrouter.instances import a_cached_sllm_gpt4o_mini__openrouter
    return design(
        a_llm_for_json_schema_example=a_cached_sllm_gpt4o__openrouter,
        a_structured_llm_for_json_fix=a_cached_sllm_gpt4o_mini__openrouter,
    )


__meta_design__ = design(
    overrides=__debug_design
)
