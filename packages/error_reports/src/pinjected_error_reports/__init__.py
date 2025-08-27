import asyncio
import hashlib
import json
from datetime import datetime
from pathlib import Path

from injected_utils import async_cached, lzma_sqlite, sqlite_dict

# Try to import voice support, but make it optional for Python 3.13 compatibility
try:
    from pinjected_niji_voice.api import NijiVoiceParam, a_niji_voice_play

    _VOICE_AVAILABLE = True
except ImportError:
    # Voice features not available (e.g., on Python 3.13 due to audioop removal)
    NijiVoiceParam = None
    a_niji_voice_play = None
    _VOICE_AVAILABLE = False

from pinjected_openai.openrouter.instances import StructuredLLM
from pinjected_openai.openrouter.util import (
    a_openrouter_chat_completion,
    a_openrouter_base_chat_completion,
)
from pydantic import BaseModel

from pinjected import *
from pinjected.schema.handlers import (
    PinjectedHandleMainException,
    PinjectedHandleMainResult,
)
from pinjected.v2.resolver import EvaluationError


class ErrorAnalysis(BaseModel):
    cause_md_simple: str
    summary_md_in_1_sentence: str
    solution_md_in_1_sentence: str


class ShortText(BaseModel):
    short_jp_msg: str


def _log_run_context(context, result=None, error=None):
    """Log the run context and result/error to .pinjected_last_run.log"""
    log_path = Path(".pinjected_last_run.log")

    log_data = {
        "timestamp": datetime.now().isoformat(),
        "context": {
            "var_path": context.src_var_spec.var_path,
            "design_bindings": list(context.design.bindings.keys()),
            "meta_overrides_bindings": list(context.meta_overrides.bindings.keys()),
            "overrides_bindings": list(context.overrides.bindings.keys()),
        },
    }

    if result is not None:
        log_data["result"] = str(result)
        log_data["status"] = "success"

    if error is not None:
        import traceback

        log_data["error"] = str(error)
        log_data["error_type"] = type(error).__name__
        log_data["traceback"] = traceback.format_exception(error)
        log_data["status"] = "error"

    with open(log_path, "w") as f:
        json.dump(log_data, f, indent=2, default=str)


@injected
async def a_handle_error_with_llm_voice(
    a_sllm_for_error_analysis: StructuredLLM,
    a_niji_voice,
    logger,
    __pinjected_error_reports_enable_voice__: bool,
    /,
    context,
    e: Exception,
):
    import traceback

    # Log the run context and error
    _log_run_context(context, error=e)

    fmt = traceback.format_exception(e)
    fmt = "".join(fmt)
    # logger.error(f"Error occurred: {e} \n {fmt}")

    async def analysis_task():
        logger.info(f"sending stacktrace to LLM for better message...")
        prompt = f"""
    こちらのエラー内容を分析してください。以下はエラーメッセージです:
    {fmt}
    回答は必ずマークダウン形式で日本語でお願いします。
        """
        resp = await a_sllm_for_error_analysis(prompt, response_format=ErrorAnalysis)
        import rich
        from rich.markdown import Markdown
        from rich.panel import Panel

        rich.print(Panel(Markdown(resp.cause_md_simple), title="Error Cause"))
        rich.print(Panel(Markdown(resp.summary_md_in_1_sentence), title="Summary"))
        rich.print(
            Panel(
                Markdown(resp.solution_md_in_1_sentence),
                title="Solution",
                style="bold green",
            )
        )

    async def play_sound_task():
        logger.info(f"playing sound for error...")
        main_e = e

        try:
            while isinstance(main_e, ExceptionGroup):
                main_e = main_e.exceptions[0]
        except NameError:
            pass
        if isinstance(main_e, EvaluationError):
            main_e = main_e.src
        err_msg = f"{main_e.__class__.__name__}"
        from pinjected.notification import notify

        if __pinjected_error_reports_enable_voice__ and _VOICE_AVAILABLE:
            voices = await asyncio.gather(
                a_niji_voice(
                    NijiVoiceParam(
                        actor_name="小夜",
                        script=f"エラー。",
                    )
                ),
                a_niji_voice(NijiVoiceParam(actor_name="小夜", script=f"{err_msg}")),
            )
            for v in voices:
                await v.a_play()
        else:
            notify(f"エラー: {err_msg}", sound="Frog")

    _ = await asyncio.gather(analysis_task(), play_sound_task())

    return "handled "


@injected
async def a_handle_result_with_llm_voice(
    a_sllm_for_error_analysis: StructuredLLM,
    a_niji_voice,
    logger,
    __pinjected_error_reports_enable_voice__: bool,
    /,
    context,
    result: object,
):
    # Log the run context and result
    _log_run_context(context, result=result)

    import rich
    from rich.errors import MarkupError
    from rich.panel import Panel

    try:
        rich.print(Panel(f"Result: {result}", title="Result", style="bold green"))
    except MarkupError:
        logger.success(f"Result: {result}")
    from pinjected.notification import notify

    if __pinjected_error_reports_enable_voice__ and _VOICE_AVAILABLE:
        voice = await a_niji_voice(
            NijiVoiceParam(
                actor_name="小夜",
                script=f"成功。",
            )
        )
        await voice.a_play()
    else:
        notify(f"成功", sound="Glass")


@instance
def __pinjected_error_reports_enable_voice__():
    return True


@instance
def test_implementation():
    raise RuntimeError("Example Exception")


@instance
def test_success_result():
    return "Example Result 2"


a_cached_openrouter_chat_completion = async_cached(
    lzma_sqlite(
        injected("error_reports_cache_path") / "openrouter_chat_completion_cache.sqlite"
    ),
    key_hashers=Injected.dict(
        response_format=lambda m: hashlib.sha256(
            str(m.model_json_schema()).encode()
        ).hexdigest()
        if m is not None
        else "None"
    ),
    replace_binding=False,
)(
    a_openrouter_chat_completion,
)

test_get_openrouter_chat_completion: IProxy = a_openrouter_chat_completion

gemini_flash_2_0 = Injected.partial(
    a_cached_openrouter_chat_completion, model="google/gemini-2.0-flash-001"
)

a_cached_sllm_gpt4o__openrouter: IProxy = async_cached(
    sqlite_dict(injected("error_reports_cache_path") / "gpt4o.sqlite")
)(Injected.partial(a_openrouter_base_chat_completion, model="openai/gpt-4o"))

# Create design with optional voice support
design_bindings = {
    PinjectedHandleMainException.key.name: a_handle_error_with_llm_voice,
    PinjectedHandleMainResult.key.name: a_handle_result_with_llm_voice,
    "a_sllm_for_error_analysis": gemini_flash_2_0,
    "error_reports_cache_path": Path("~/.cache").expanduser(),
    "cache_root_path": Path("~/.cache").expanduser(),
    "a_llm_for_json_schema_example": a_cached_sllm_gpt4o__openrouter,
    "a_structured_llm_for_json_fix": a_cached_sllm_gpt4o__openrouter,
}

# Only add voice support if available
if _VOICE_AVAILABLE:
    design_bindings["a_niji_voice_play"] = a_niji_voice_play
else:
    # Provide a dummy voice function that does nothing when voice is not available
    @instance
    async def dummy_a_niji_voice(param):
        return None

    design_bindings["a_niji_voice"] = dummy_a_niji_voice

design_for_error_reports = design(**design_bindings)
