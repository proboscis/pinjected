from pathlib import Path
from typing import Any, Optional, Type
import os
import sys
import json
import pytest
import httpx
from pydantic import BaseModel

from pinjected import design, injected
from pinjected.pytest_fixtures import register_fixtures_from_design
from pinjected.picklable_logger import PicklableLogger
from pinjected_openai.openrouter.util import (
    OpenRouterModelTable,
    OpenRouterModel,
    OpenRouterArchitecture,
    OpenRouterCapabilities,
    OpenRouterModelPricing,
    OpenRouterProviderInfo,
)

APIKEY = pytest.mark.APIKEY


def should_skip_apikey_tests() -> bool:
    return bool(os.environ.get("CI")) or sys.platform != "darwin"


def apikey_skip_if_needed():
    if should_skip_apikey_tests():
        pytest.skip(
            "Requires API key; skipped in CI and non-darwin environments",
            allow_module_level=True,
        )


class _MockResponse:
    def __init__(
        self, json_data: dict, status_code: int = 200, headers: Optional[dict] = None
    ):
        self._json = json_data
        self.status_code = status_code
        self.headers = headers or {"content-type": "application/json"}
        self.text = (
            json.dumps(self._json)
            if "application/json" in self.headers.get("content-type", "").lower()
            else ""
        )

    def json(self):
        return self._json

    def raise_for_status(self):
        if not (200 <= self.status_code < 300):
            raise httpx.HTTPStatusError("error", request=None, response=None)


class _MockAsyncClient:
    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url: str, *args, **kwargs):
        if "openrouter.ai/api/v1/models" in url:
            data = {
                "data": [
                    {
                        "id": "openai/gpt-4o-mini",
                        "name": "GPT-4o Mini",
                        "context_length": 128000,
                        "architecture": {
                            "name": "gpt-4o",
                            "capabilities": {"json": True},
                        },
                        "pricing": {"prompt": 0.00001, "completion": 0.00003},
                    },
                    {
                        "id": "openai/gpt-4o",
                        "name": "GPT-4o",
                        "context_length": 128000,
                        "architecture": {
                            "name": "gpt-4o",
                            "capabilities": {"json": True},
                        },
                        "pricing": {"prompt": 0.00002, "completion": 0.00006},
                    },
                    {
                        "id": "openai/gpt-4-turbo",
                        "name": "GPT-4 Turbo",
                        "context_length": 128000,
                        "architecture": {
                            "name": "gpt-4",
                            "capabilities": {"json": True},
                        },
                        "pricing": {"prompt": 0.00002, "completion": 0.00006},
                    },
                    {
                        "id": "openai/gpt-3.5-turbo",
                        "name": "GPT-3.5 Turbo",
                        "context_length": 16385,
                        "architecture": {
                            "name": "gpt-3.5",
                            "capabilities": {"json": True},
                        },
                        "pricing": {"prompt": 0.000001, "completion": 0.000002},
                    },
                    {
                        "id": "meta-llama/llama-3-8b-instruct",
                        "name": "Llama 3 8B Instruct",
                        "context_length": 8192,
                        "architecture": {
                            "name": "llama",
                            "capabilities": {"json": False},
                        },
                        "pricing": {"prompt": 0.0, "completion": 0.0},
                    },
                    {
                        "id": "google/gemini-pro",
                        "name": "Gemini Pro",
                        "context_length": 128000,
                        "architecture": {
                            "name": "gemini",
                            "capabilities": {"json": False},
                        },
                        "pricing": {"prompt": 0.0, "completion": 0.0},
                    },
                ]
            }
            return _MockResponse(data, 200, {"content-type": "application/json"})
        return _MockResponse({"data": []})

    async def post(self, url: str, *args, **kwargs):
        return _MockResponse(
            {
                "choices": [
                    {"message": {"role": "assistant", "content": "Mock response"}}
                ],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1},
            },
            200,
            {"content-type": "application/json"},
        )


@pytest.fixture(autouse=True)
def _patch_httpx_async_client(monkeypatch):
    monkeypatch.setattr(httpx, "AsyncClient", _MockAsyncClient)
    yield


@pytest.fixture(scope="function")
def _cache_root_path(tmp_path_factory) -> Path:
    base = Path.home() / ".cache" / "pinjected_openai_support"
    base.mkdir(parents=True, exist_ok=True)
    return tmp_path_factory.mktemp("openai_support_cache", dir=base)


async def _mock_openrouter_post(payload: dict) -> dict:
    return {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "Mock response",
                }
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        "provider": "openai",
    }


def _build_sample_for_model(model_cls: Type[BaseModel]) -> dict:
    fields = getattr(model_cls, "model_fields", {})
    sample: dict[str, Any] = {}
    for name, field in fields.items():
        anno = field.annotation
        anno_str = str(anno)
        if anno is str:
            sample[name] = "test"
        elif anno is int:
            sample[name] = 1
        elif anno is float:
            sample[name] = 0.5
        elif anno is bool:
            sample[name] = True
        elif (
            anno_str.startswith("typing.Optional")
            or anno_str.startswith("typing.Union")
            or "NoneType" in anno_str
        ):
            if "int" in anno_str:
                sample[name] = 1
            elif "float" in anno_str:
                sample[name] = 0.5
            elif "str" in anno_str:
                sample[name] = None
            else:
                sample[name] = None
        elif anno_str.startswith("typing.List") or anno_str.startswith("list"):
            sample[name] = []
        elif anno is dict or "Dict" in anno_str or anno_str == "dict":
            sample[name] = {}
        else:
            try:
                sample[name] = anno()
            except Exception:
                sample[name] = None
    return sample


async def _mock_openrouter_chat_completion(
    prompt: Optional[str] = None,
    text: Optional[str] = None,
    model: str = "openai/gpt-4o-mini",
    images=None,
    response_format: Optional[Type[BaseModel]] = None,
    max_tokens: int = 8192,
    temperature: float = 0,
    **kwargs: Any,
):
    if response_format is not None:
        sample = _build_sample_for_model(response_format)
        return response_format.model_validate(sample)
    return "Mock response"


def _model_table_fixture() -> OpenRouterModelTable:
    entries = [
        ("openai/gpt-4o-mini", "GPT-4o Mini", "gpt-4o", True, 128000, 0.00001, 0.00003),
        ("openai/gpt-4o", "GPT-4o", "gpt-4o", True, 128000, 0.00002, 0.00006),
        ("openai/gpt-4-turbo", "GPT-4 Turbo", "gpt-4", True, 128000, 0.00002, 0.00006),
        (
            "openai/gpt-3.5-turbo",
            "GPT-3.5 Turbo",
            "gpt-3.5",
            True,
            16385,
            0.000001,
            0.000002,
        ),
        (
            "meta-llama/llama-3-8b-instruct",
            "Llama 3 8B Instruct",
            "llama",
            False,
            8192,
            0.0,
            0.0,
        ),
        ("google/gemini-pro", "Gemini Pro", "gemini", False, 128000, 0.0, 0.0),
    ]
    models = []
    for id_, name, arch_name, json_cap, ctx_len, p_prompt, p_comp in entries:
        caps = OpenRouterCapabilities(json=json_cap)
        arch = OpenRouterArchitecture(
            name=arch_name, modality="", tokenizer="", capabilities=caps
        )
        pricing = OpenRouterModelPricing(prompt=f"{p_prompt}", completion=f"{p_comp}")
        models.append(
            OpenRouterModel(
                id=id_,
                name=name,
                created=0,
                description="",
                context_length=ctx_len,
                architecture=arch,
                pricing=pricing,
                top_provider=OpenRouterProviderInfo(
                    name="openai", url="https://api", icon=None, context_length=ctx_len
                ),
                per_request_limits=None,
                supported_parameters=None,
            )
        )
    return OpenRouterModelTable(data=models)


def _test_design(cache_root: Path):
    class _MockOpenAICompletions:
        async def create(self, *args, **kwargs):
            return {
                "choices": [{"message": {"content": "Mock response"}}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1},
            }

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

    _mock_beta_parse = _MockOpenAIBetaChatCompletionsParse()

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
                                "BComp", (), {"parse": _mock_beta_parse}
                            )()
                        },
                    )()
                },
            )()

    base = design(
        logger=PicklableLogger(),
        openrouter_api_key="dummy-key",
        cache_root_path=cache_root,
        openrouter_timeout_sec=120.0,
        openrouter_state=dict(),
        a_openrouter_post=_mock_openrouter_post,
        a_openrouter_chat_completion=_mock_openrouter_chat_completion,
        openrouter_model_table=_model_table_fixture(),
        openai_config__personal={"api_key": "dummy", "organization": None},
        openai_config={"api_key": "dummy", "organization": None},
        openai_api_key="dummy",
        openai_organization=None,
        async_openai_client=_MockOpenAIClient(),
    )
    return base + design(
        a_llm_for_json_schema_example=injected("a_openrouter_chat_completion"),
        a_structured_llm_for_json_fix=injected("a_openrouter_chat_completion"),
    )


fixtures = register_fixtures_from_design(_test_design(injected("_cache_root_path")))
