"""Unit tests for GPT-5 structured output support via OpenRouter utilities."""

import pytest
from pydantic import BaseModel

from pinjected_openai.openrouter import util as openrouter_util
from pinjected_openai.openrouter.util import (
    OpenRouterArchitecture,
    OpenRouterCapabilities,
    OpenRouterModel,
    OpenRouterModelPricing,
    OpenRouterModelTable,
    clear_false_json_claims_cache,
)


class SimpleResponse(BaseModel):
    """Mock structured response schema."""

    answer: str
    confidence: float


class DummyLogger:
    """Minimal logger capturing warnings for assertions if needed."""

    def __init__(self):
        self.messages = []

    def debug(self, message: str) -> None:  # pragma: no cover - trivial
        self.messages.append(("debug", message))

    def info(self, message: str) -> None:  # pragma: no cover - trivial
        self.messages.append(("info", message))

    def warning(self, message: str) -> None:
        self.messages.append(("warning", message))

    def error(self, message: str) -> None:  # pragma: no cover - trivial
        self.messages.append(("error", message))


@pytest.mark.asyncio
async def test_gpt5_mini_structured_output_uses_fallback():
    """Ensure GPT-5 mini still yields structured output via JSON fallback."""

    clear_false_json_claims_cache()

    gpt5_model = OpenRouterModel(
        id="openai/gpt-5-mini",
        name="GPT-5 Mini",
        created=0,
        description="Mock GPT-5 Mini entry",
        context_length=128_000,
        architecture=OpenRouterArchitecture(
            modality="text",
            tokenizer="gpt-5",
            instruct_type=None,
            input_modalities=["text"],
            output_modalities=["text"],
            capabilities=OpenRouterCapabilities(json=True),
        ),
        pricing=OpenRouterModelPricing(prompt="0.001", completion="0.002"),
        providers=None,
        per_request_limits=None,
        supported_parameters=["response_format", "structured_outputs"],
    )

    model_table = OpenRouterModelTable(data=[gpt5_model])

    call_state = {"count": 0}

    async def fake_base_chat_completion(
        *,
        prompt: str,
        model: str,
        max_tokens: int = 0,
        temperature: float = 0,
        images=None,
        response_format=None,
        provider=None,
        include_reasoning: bool = False,
        reasoning=None,
        **kwargs,
    ) -> str:
        call_state["count"] += 1
        if call_state["count"] == 1 and response_format is not None:
            raise RuntimeError("404 No endpoints found for structured output")
        return '{"answer": "Paris", "confidence": 0.95}'

    async def fake_schema_example_provider(model_schema: dict) -> str:
        return "{}"

    async def fake_json_fix(prompt: str) -> str:
        return '{"answer": "Paris", "confidence": 0.95}'

    logger = DummyLogger()

    result = await openrouter_util.a_openrouter_chat_completion.src_function(
        openrouter_util._build_structured_request_context.src_function,
        openrouter_util._parse_structured_output.src_function,
        fake_base_chat_completion,
        model_table,
        fake_schema_example_provider,
        fake_json_fix,
        logger,
        prompt="What is the capital of France?",
        model="openai/gpt-5-mini",
        response_format=SimpleResponse,
        max_tokens=100,
        temperature=0,
    )

    assert isinstance(result, SimpleResponse)
    assert result.answer.lower() == "paris"
    assert result.confidence == pytest.approx(0.95)
    assert call_state["count"] == 2  # first call failed, fallback succeeded
    warnings = [message for level, message in logger.messages if level == "warning"]
    assert any(
        "claims JSON support but returns 404" in message for message in warnings
    ), warnings
    assert "openai/gpt-5-mini" in openrouter_util._models_with_false_json_claims
