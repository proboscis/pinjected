import time
from typing import Protocol

from httpx import ReadTimeout
from injected_utils import async_cached, lzma_sqlite, sqlite_dict
from pinjected import injected, Injected, IProxy, design
from pydantic import BaseModel

from pinjected_openai.openrouter.util import a_openrouter_chat_completion__without_fix, Text


class NoEndpointsFoundError(Exception):
    pass


class StructuredLLM(Protocol):
    async def __call__(self, text: str, model: str, images=None, response_format: type[BaseModel] = None,
                       max_tokens: int = 8192):
        ...


@injected
async def a_sllm_openrouter(
        a_openrouter_chat_completion,
        logger,
        /,
        text: str,
        model: str,
        images=None,
        response_format: type[BaseModel] = None,
        max_tokens: int = 8192,
):
    retry_count = 5
    while retry_count:
        try:
            return await a_openrouter_chat_completion(
                text,
                response_format=response_format,
                # model='google/gemini-2.0-flash-001',
                images=images,
                model=model,
                max_tokens=max_tokens
            )
        except ReadTimeout as e:
            logger.warning(f"Timeout error for {a_openrouter_chat_completion.__name__}: {e}")
            time.sleep(1)
        except Exception as e:
            import traceback
            trc = traceback.format_exc()
            logger.warning(f"Remaining ({retry_count}) for {a_openrouter_chat_completion.__name__}: {e} \n {trc}")
            if 'No endpoints found' in str(e):
                raise NoEndpointsFoundError(f"No endpoints found for {model} with {response_format}") from e
            retry_count -= 1
            if not retry_count:
                raise e
            # if not retry_count:
            # raise RuntimeError(f"Failed to run {a_openrouter_chat_completion.__name__} after 5 retries.") from e


a_cached_structured_llm__gemini_flash_2_0: IProxy[StructuredLLM] = async_cached(
    lzma_sqlite(injected('cache_root_path') / "gemini_flash.sqlite"))(
    Injected.partial(a_sllm_openrouter, model='google/gemini-2.0-flash-001')
)
a_cached_structured_llm__deepseek_chat: IProxy[StructuredLLM] = async_cached(
    lzma_sqlite(injected('cache_root_path') / "deepseek_chat.sqlite"))(
    Injected.partial(a_sllm_openrouter, model='deepseek/deepseek-chat')
)
a_cached_structured_llm__gemini_flash_thinking_2_0: IProxy[StructuredLLM] = async_cached(
    lzma_sqlite(injected('cache_root_path') / "gemini_flash_thinking.sqlite"))(
    Injected.partial(a_sllm_openrouter, model='google/gemini-2.0-flash-thinking-exp:free')
)
a_cached_structured_llm__claude_sonnet_3_5: IProxy[StructuredLLM] = async_cached(
    lzma_sqlite(injected('cache_root_path') / "claude_sonnet_3_5.sqlite"))(
    Injected.partial(a_sllm_openrouter, model='anthropic/claude-3.5-sonnet')
)
a_cached_sllm_gpt4o__openrouter: IProxy = async_cached(sqlite_dict(injected('cache_root_path') / "gpt4o.sqlite"))(
    Injected.partial(
        a_openrouter_chat_completion__without_fix,
        model="openai/gpt-4o"
    )
)

a_cached_sllm_gpt4o_mini__openrouter: IProxy = async_cached(
    sqlite_dict(injected('cache_root_path') / "gpt4o_mini.sqlite"))(
    Injected.partial(
        a_openrouter_chat_completion__without_fix,
        model="openai/gpt-4o-mini"
    )
)

test_cached_sllm_gpt4o_mini: IProxy = a_cached_sllm_gpt4o_mini__openrouter(
    prompt="What is the capital of Japan?",
    model="openai/gpt-4o-mini"
)
test_cached_sllm_gpt4o: IProxy = a_cached_sllm_gpt4o__openrouter(
    prompt="What is the capital of Japan?",
    model="openai/gpt-4o"
)

test_gemini_flash_2_0_structured:IProxy = a_cached_structured_llm__gemini_flash_2_0(
    text="What is the capital of Japan? v2",
    response_format=Text
)

__meta_design__ = design(
    overrides=design(
        a_llm_for_json_schema_example=a_cached_sllm_gpt4o__openrouter,
        a_structured_llm_for_json_fix=a_cached_sllm_gpt4o_mini__openrouter,
        # openai_config=injected('openai_config__personal')
    )
)
