from pathlib import Path

from pinjected import DesignSpec, design
from pinjected.picklable_logger import PicklableLogger
from packages.openai_support.conftest import (
    _mock_openrouter_post,
    _mock_openrouter_chat_completion,
    _model_table_fixture,
)


class _MockOpenAIBetaChatCompletionsParse:
    async def __call__(self, *args, **kwargs):
        class _Parsed:
            def __init__(self):
                self.choices = [
                    type(
                        "M",
                        (),
                        {
                            "message": type(
                                "Msg",
                                (),
                                {"parsed": {"answer": "test", "confidence": 0.9}},
                            )()
                        },
                    )
                ]

        return _Parsed()


class _MockOpenAICompletions:
    async def create(self, *args, **kwargs):
        import json

        class _Usage:
            def __init__(self, prompt=1, completion=1, reasoning=None):
                self.prompt_tokens = prompt
                self.completion_tokens = completion

                class _Details:
                    def __init__(self, reasoning_tokens):
                        self.reasoning_tokens = reasoning_tokens

                self.completion_tokens_details = _Details(reasoning)

            def model_dump(self):
                d = {
                    "prompt_tokens": self.prompt_tokens,
                    "completion_tokens": self.completion_tokens,
                }
                if (
                    self.completion_tokens_details
                    and getattr(
                        self.completion_tokens_details, "reasoning_tokens", None
                    )
                    is not None
                ):
                    d["completion_tokens_details"] = {
                        "reasoning_tokens": self.completion_tokens_details.reasoning_tokens
                    }
                return d

        class _Message:
            def __init__(self, content=None, parsed=None):
                self.content = content
                self.parsed = parsed

        class _Choice:
            def __init__(self, message):
                self.message = message

        class _Resp:
            def __init__(self, content, usage):
                self.choices = [_Choice(_Message(content=content))]
                self.usage = usage

        if kwargs.get("response_format"):
            rf = kwargs["response_format"]
            schema_name = None
            if isinstance(rf, dict):
                schema_name = rf.get("json_schema", {}).get("name")
            elif hasattr(rf, "__name__"):
                schema_name = rf.__name__
            if schema_name == "CityInfo":
                content = json.dumps(
                    {"city": "Paris", "country": "France", "is_capital": True}
                )
            elif schema_name in {"SimpleResponse", "SimpleAnswer"}:
                content = json.dumps({"answer": "The sky is blue.", "confidence": 0.9})
            else:
                content = json.dumps({"ok": True})
        else:
            content = "Mock response"
        model = kwargs.get("model", "")
        reasoning = 5 if "gpt-5" in model or "o1" in model else None
        return _Resp(content, _Usage(prompt=1, completion=1, reasoning=reasoning))


class _MockOpenAIClient:
    def __init__(self):
        self.chat = type("Chat", (), {"completions": _MockOpenAICompletions()})()
        self.beta = type(
            "Beta",
            (),
            {
                "chat": type(
                    "BChat",
                    (),
                    {
                        "completions": type(
                            "BComp",
                            (),
                            {"parse": _MockOpenAIBetaChatCompletionsParse()},
                        )()
                    },
                )()
            },
        )()


cache_root = Path.home() / ".cache" / "pinjected_openai_support"
cache_root.mkdir(parents=True, exist_ok=True)


async def _a_test_openrouter_model_table():
    return _model_table_fixture()


__design__ = design(
    logger=PicklableLogger(),
    openrouter_api_key="dummy-key",
    cache_root_path=cache_root,
    openrouter_timeout_sec=120.0,
    openrouter_state=dict(),
    a_openrouter_post=_mock_openrouter_post,
    a_openrouter_chat_completion=_mock_openrouter_chat_completion,
    openrouter_model_table=_model_table_fixture(),
    test_openrouter_model_table=_a_test_openrouter_model_table,
    openai_config__personal={"api_key": "dummy", "organization": None},
    openai_config={"api_key": "dummy", "organization": None},
    openai_api_key="dummy",
    openai_organization=None,
    async_openai_client=_MockOpenAIClient(),
)

__design_spec__ = DesignSpec.empty()
