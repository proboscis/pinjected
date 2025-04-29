from pathlib import Path

from injected_utils import async_cached, lzma_sqlite
from injected_utils.progress import a_map_progress__tqdm
from pinjected_openai.openrouter.instances import (
    a_cached_structured_llm__gemini_flash_2_0,
)

from pinjected import Injected, design, injected, instance
from pinjected_reviewer.git_util import git_info
from pinjected_reviewer.models import a_cached_openrouter_chat_completion


@instance
async def cache_root_path():
    path = Path("~/.cache/pinjected_reviewer").expanduser()
    path.mkdir(exist_ok=True, parents=True)
    return path


@instance
def __pinjected_reviewer_default_design():
    # pinjected-reviewer: ignore
    from loguru import logger
    from pinjected_openai.openrouter.util import (
        a_openrouter_chat_completion,
        a_openrouter_chat_completion__without_fix,
    )

    from pinjected_reviewer.pytest_reviewer.inspect_code import a_symbol_metadata_getter
    from pinjected_reviewer.reviewer_v1 import pinjected_guide_md

    return design(
        a_sllm_for_commit_review=async_cached(
            lzma_sqlite(injected("cache_root_path") / "a_sllm_for_commit_review.sqlite")
        )(
            Injected.partial(
                a_openrouter_chat_completion,
                model="anthropic/claude-3.7-sonnet:thinking",
            )
        ),
        a_sllm_for_approval_extraction=async_cached(
            lzma_sqlite(
                injected("cache_root_path") / "a_sllm_for_approval_extraction.sqlite"
            )
        )(
            Injected.partial(
                a_openrouter_chat_completion,
                model="google/gemini-2.0-flash-001",
            )
        ),
        a_structured_llm_for_json_fix=async_cached(
            lzma_sqlite(
                injected("cache_root_path") / "a_structured_llm_for_json_fix.sqlite"
            )
        )(
            Injected.partial(
                a_openrouter_chat_completion__without_fix, model="openai/gpt-4o-mini"
            )
        ),
        a_llm_for_json_schema_example=async_cached(
            lzma_sqlite(
                injected("cache_root_path") / "a_llm_for_json_schema_example.sqlite"
            )
        )(
            Injected.partial(
                a_openrouter_chat_completion__without_fix,
                model="openai/gpt-4o",
            )
        ),
        a_sllm_for_code_review=injected("a_sllm_for_commit_review"),
        a_sllm_for_markdown_extraction=injected(
            "a_sllm_for_commit_review"
        ),  # For reviewer markdown extraction
        logger=logger,
        pinjected_guide_md=pinjected_guide_md,
        a_symbol_metadata_getter=a_symbol_metadata_getter,
        repo_root=Path.cwd(),
        a_map_progress=a_map_progress__tqdm,
        a_cached_openrouter_chat_completion=a_cached_openrouter_chat_completion,
        pinjected_reviewer_cache_path=Path("~/.cache/pinjected_reviewer").expanduser(),
        git_info=git_info,
    )


__design__ = design(
    a_structured_llm_for_markdown_extraction=a_cached_structured_llm__gemini_flash_2_0
)
