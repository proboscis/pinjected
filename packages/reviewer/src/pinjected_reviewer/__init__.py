"""
pinjected-reviewer - A git pre-commit hook for reviewing code with pinjected.
"""
from pathlib import Path

from injected_utils import async_cached, lzma_sqlite
from pinjected import design, instance, injected, Injected

__version__ = "0.3.1"

# This allows utils to be imported properly from the package
from pinjected_reviewer.utils import check_if_file_should_be_ignored


@instance
async def cache_root_path():
    path = Path("~/.cache/pinjected_reviewer").expanduser()
    path.mkdir(exist_ok=True, parents=True)
    return path


@instance
def __pinjected_reviewer_default_design():
    # pinjected-reviewer: ignore
    from pinjected_reviewer.entrypoint import pinjected_guide_md
    from pinjected_openai.openrouter.util import a_openrouter_chat_completion
    from pinjected_openai.openrouter.util import a_openrouter_chat_completion__without_fix
    from pinjected_reviewer.pytest_reviewer.inspect_code import a_symbol_metadata_getter
    from loguru import logger
    return design(
        a_sllm_for_commit_review=async_cached(
            lzma_sqlite(injected('cache_root_path') / 'a_sllm_for_commit_review.sqlite'))(
            Injected.partial(
                a_openrouter_chat_completion,
                model="anthropic/claude-3.7-sonnet:thinking"
            )
        ),
        a_sllm_for_approval_extraction=async_cached(
            lzma_sqlite(injected('cache_root_path') / 'a_sllm_for_approval_extraction.sqlite'))(
            Injected.partial(
                a_openrouter_chat_completion,
                model="google/gemini-2.0-flash-001",
            )
        ),
        a_structured_llm_for_json_fix=async_cached(
            lzma_sqlite(injected('cache_root_path') / 'a_structured_llm_for_json_fix.sqlite'))(
            Injected.partial(
                a_openrouter_chat_completion__without_fix,
                model="openai/gpt-4o-mini"
            )
        ),
        a_llm_for_json_schema_example=async_cached(
            lzma_sqlite(injected('cache_root_path') / 'a_llm_for_json_schema_example.sqlite'))(
            Injected.partial(
                a_openrouter_chat_completion__without_fix,
                model="openai/gpt-4o",
            )
        ),
        a_sllm_for_code_review=injected('a_sllm_for_commit_review'),
        logger=logger,
        pinjected_guide_md=pinjected_guide_md,
        a_symbol_metadata_getter=a_symbol_metadata_getter
    )


__meta_design__ = design(
    overrides=__pinjected_reviewer_default_design
)
