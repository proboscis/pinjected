"""End-to-end verification that GPT-5 models accept structured output via OpenRouter."""

import json
from unittest.mock import patch

import httpx
import pytest
from httpx._client import (
    AsyncClient as RealAsyncClient,
)  # bypass test-time httpx patching
from pinjected import design, injected
from pinjected.test import injected_pytest
from pydantic import BaseModel

from packages.openai_support.conftest import apikey_skip_if_needed
from pinjected_openai.openrouter.util import (
    OpenRouterModelTable,
    a_openrouter_chat_completion,
    clear_false_json_claims_cache,
)


pytestmark = pytest.mark.e2e
apikey_skip_if_needed()


class SimpleResponse(BaseModel):
    """Minimal schema to validate structured JSON output."""

    answer: str
    confidence: float


@pytest.mark.asyncio
@injected_pytest(design(openrouter_api_key=injected("openrouter_api_key__company")))
async def test_openrouter_gpt5_structured_response(
    openrouter_api_key: str,
    logger,
    /,
) -> None:
    """Ensure GPT-5 models report and honour structured output support."""
    headers = {
        "Authorization": f"Bearer {openrouter_api_key}",
        "Content-Type": "application/json",
    }

    async with RealAsyncClient(timeout=60.0) as client:
        # Check capability metadata first
        models_resp = await client.get("https://openrouter.ai/api/v1/models")
        models_resp.raise_for_status()
        models_data = models_resp.json().get("data", [])

        gpt5_models = {
            m["id"]: m.get("supported_parameters", [])
            for m in models_data
            if m.get("id", "").startswith("openai/gpt-5")
        }
        assert gpt5_models, "No GPT-5 models returned from OpenRouter /models endpoint"

        for model_id, params in gpt5_models.items():
            assert "response_format" in params, (
                f"{model_id} missing response_format support flag"
            )
            assert "structured_outputs" in params, (
                f"{model_id} missing structured_outputs support flag"
            )

        # Run a live structured-output request against the smallest GPT-5 tier
        payload = {
            "model": "openai/gpt-5-nano",
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "Return the capital city of France and your confidence as JSON."
                        " Ensure the answer field contains 'Paris'."
                    ),
                }
            ],
            "max_completion_tokens": 512,
            "temperature": 0,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "SimpleResponse",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "answer": {"type": "string"},
                            "confidence": {"type": "number"},
                        },
                        "required": ["answer", "confidence"],
                        "additionalProperties": False,
                    },
                },
            },
        }

        completion_resp = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
        )
        completion_resp.raise_for_status()
        body = completion_resp.json()
        logger.info(
            "OpenRouter GPT-5 structured response metadata: %s"
            % json.dumps(
                {
                    "id": body.get("id"),
                    "provider": body.get("provider"),
                    "usage": body.get("usage"),
                }
            )
        )

        # Handle top-level errors
        if "error" in body:
            pytest.fail(f"OpenRouter returned error: {body['error']}")

        choices = body.get("choices", [])
        assert choices, (
            f"No choices in OpenRouter response: {json.dumps(body, indent=2)}"
        )
        choice = choices[0]

        # If provider reports insufficient quota, mark the test as skipped (environmental)
        if "error" in choice:
            raw = choice["error"].get("metadata", {}).get("raw", {})
            if raw.get("code") == "insufficient_quota":
                pytest.fail("OpenAI quota exhausted for GPT-5 structured output test")
            pytest.fail(f"Error in choice payload: {json.dumps(choice, indent=2)}")

        content = choice.get("message", {}).get("content", "")
        if not content.strip():
            pytest.fail("GPT-5 returned empty content for structured output")

    parsed = SimpleResponse.model_validate_json(content)
    assert "paris" in parsed.answer.lower(), parsed
    assert parsed.confidence >= 0, parsed


@pytest.mark.asyncio
@injected_pytest(design(openrouter_api_key=injected("openrouter_api_key__personal")))
async def test_openrouter_gpt5_structured_via_chat_completion(
    a_openrouter_base_chat_completion,
    a_cached_schema_example_provider,
    a_structured_llm_for_json_fix,
    logger,
    openrouter_api_key,
    /,
) -> None:
    """Exercise a_openrouter_chat_completion with live GPT-5 structured output."""
    clear_false_json_claims_cache()

    async with RealAsyncClient(timeout=60.0) as client:
        models_resp = await client.get(
            "https://openrouter.ai/api/v1/models",
            headers={"Authorization": f"Bearer {openrouter_api_key}"},
        )
        models_resp.raise_for_status()
        model_table = OpenRouterModelTable.model_validate(
            {"data": models_resp.json().get("data", [])}
        )

    with patch.object(httpx, "AsyncClient", RealAsyncClient, create=True):
        result = await a_openrouter_chat_completion.src_function(
            a_openrouter_base_chat_completion,
            model_table,
            a_cached_schema_example_provider,
            a_structured_llm_for_json_fix,
            logger,
            prompt="Respond in JSON with fields answer and confidence for the capital of France.",
            model="openai/gpt-5",
            response_format=SimpleResponse,
            max_tokens=256,
            temperature=0,
        )

    assert isinstance(result, SimpleResponse)
    assert "paris" in result.answer.lower(), result
    assert result.confidence >= 0, result
