import asyncio
import hashlib
from pathlib import Path

from injected_utils import async_cached, lzma_sqlite, sqlite_dict
from pinjected import *
from pinjected.schema.handlers import PinjectedHandleMainException, PinjectedHandleMainResult
from pinjected.v2.resolver import EvaluationError
from pinjected_niji_voice.api import a_niji_voice_play, NijiVoiceParam
from pinjected_openai.openrouter.instances import StructuredLLM
from pinjected_openai.openrouter.util import a_openrouter_chat_completion, a_openrouter_chat_completion__without_fix
from pydantic import BaseModel


class ErrorAnalysis(BaseModel):
    cause_md_simple: str
    summary_md_in_1_sentence: str
    solution_md_in_1_sentence: str


class ShortText(BaseModel):
    short_jp_msg: str


@injected
async def a_handle_error_with_llm_voice(
        a_sllm_for_error_analysis: StructuredLLM,
        a_niji_voice,
        logger,
        __pinjected_error_reports_enable_voice__:bool,
        /,
        e: Exception
):
    import traceback
    fmt = traceback.format_exception(e)
    fmt = "".join(fmt)
    logger.error(f"Error occurred: {e} \n {fmt}")

    async def analysis_task():
        prompt = f"""
    こちらのエラー内容を分析してください。以下はエラーメッセージです:
    {fmt}
    回答は必ずマークダウン形式で日本語でお願いします。
        """
        resp = await a_sllm_for_error_analysis(prompt, response_format=ErrorAnalysis)
        import rich
        from rich.panel import Panel
        from rich.markdown import Markdown
        rich.print(Panel(Markdown(resp.cause_md_simple), title="Error Cause"))
        rich.print(Panel(Markdown(resp.summary_md_in_1_sentence), title="Summary"))
        rich.print(Panel(Markdown(resp.solution_md_in_1_sentence), title="Solution", style="bold green"))

    async def play_sound_task():
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
        if __pinjected_error_reports_enable_voice__:
            voices = await asyncio.gather(
                a_niji_voice(NijiVoiceParam(
                    actor_name='小夜',
                    script=f'エラー。',
                )),
                a_niji_voice(NijiVoiceParam(
                    actor_name='小夜',
                    script=f"{err_msg}"
                ))
            )
            for v in voices:
                await v.a_play()
        else:
            notify(f"エラー: {err_msg}", sound='Frog')

    _ = await asyncio.gather(analysis_task(), play_sound_task())

    return "handled "

@injected
async def a_handle_result_with_llm_voice(
        a_sllm_for_error_analysis: StructuredLLM,
        a_niji_voice,
        logger,
        __pinjected_error_reports_enable_voice__:bool,
        /,
        result: object
):
    import rich
    from rich.panel import Panel
    rich.print(Panel(f"Result: {result}", title="Result",style="bold green"))
    from pinjected.notification import notify
    if __pinjected_error_reports_enable_voice__:
        voice = await a_niji_voice(NijiVoiceParam(
            actor_name='小夜',
            script=f"成功。",
        ))
        await voice.a_play()
    else:
        notify(f"成功", sound='Glass')

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
    lzma_sqlite(injected('error_reports_cache_path') / "openrouter_chat_completion_cache.sqlite"),
    key_hashers=Injected.dict(
        response_format=lambda m: hashlib.sha256(str(m.model_json_schema()).encode()).hexdigest()
    )
)(
    a_openrouter_chat_completion,
)

test_get_openrouter_chat_completion: IProxy = a_openrouter_chat_completion

gemini_flash_2_0 = Injected.partial(
    a_cached_openrouter_chat_completion,
    model='google/gemini-2.0-flash-001'
)

a_cached_sllm_gpt4o__openrouter: IProxy = async_cached(sqlite_dict(
    injected('error_reports_cache_path') / "gpt4o.sqlite")
)(
    Injected.partial(
        a_openrouter_chat_completion__without_fix,
        model="openai/gpt-4o"
    )
)

design_for_error_reports = design(
    **{
        PinjectedHandleMainException.key.name: a_handle_error_with_llm_voice,
        PinjectedHandleMainResult.key.name: a_handle_result_with_llm_voice
    },
    a_sllm_for_error_analysis=gemini_flash_2_0,
    a_niji_voice_play=a_niji_voice_play,
    error_reports_cache_path=Path("~/.cache").expanduser(),
    cache_root_path=Path("~/.cache").expanduser(),
    a_llm_for_json_schema_example=a_cached_sllm_gpt4o__openrouter,
    a_structured_llm_for_json_fix=a_cached_sllm_gpt4o__openrouter,
)

__meta_design__ = design(
    # overrides=design_for_error_reports
    overrides = design(

    )
)