"""End-to-end test: GPT-5 structured output using a Pydantic BaseModel schema."""

import json

import pytest
from httpx import AsyncClient
from pinjected import design, injected
from pinjected.test import injected_pytest
from pydantic import BaseModel

from packages.openai_support.conftest import apikey_skip_if_needed
from pinjected_openai.openrouter.util import build_openrouter_response_format


pytestmark = pytest.mark.e2e
apikey_skip_if_needed()


class SimpleResponse(BaseModel):
    """Minimal schema for GPT-5 structured output checks."""

    answer: str
    confidence: float


@pytest.mark.asyncio
@injected_pytest(design(openrouter_api_key=injected("openrouter_api_key__personal")))
async def test_openrouter_gpt5_structured_with_basemodel(
    openrouter_api_key: str,
    logger,
    /,
) -> None:
    """Send a BaseModel-derived response_format to OpenRouter GPT-5."""
    headers = {
        "Authorization": f"Bearer {openrouter_api_key}",
        "Content-Type": "application/json",
    }

    # Build response_format from the BaseModel using the same helper as production code
    response_format = build_openrouter_response_format(SimpleResponse)

    payload = {
        "model": "openai/gpt-5-nano",
        "messages": [
            {
                "role": "user",
                "content": (
                    "Return the capital city of France as JSON with a confidence score."
                ),
            }
        ],
        "max_completion_tokens": 512,
        "temperature": 0,
        "response_format": response_format,
    }

    async with AsyncClient(timeout=60.0) as client:
        completion_resp = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
        )
        completion_resp.raise_for_status()
        body = completion_resp.json()
        logger.info(
            "OpenRouter GPT-5 BaseModel response metadata: %s"
            % json.dumps(
                {
                    "id": body.get("id"),
                    "provider": body.get("provider"),
                    "usage": body.get("usage"),
                }
            )
        )

    if "error" in body:
        error = body["error"]
        if (
            isinstance(error, dict)
            and error.get("metadata", {}).get("raw", {}).get("code")
            == "insufficient_quota"
        ):
            pytest.fail("GPT-5 structured BaseModel request failed: insufficient quota")
        pytest.fail(f"OpenRouter returned error: {json.dumps(error, indent=2)}")

    choices = body.get("choices", [])
    if not choices:
        pytest.fail("No choices returned from GPT-5 structured BaseModel call")

    choice = choices[0]
    message = choice.get("message", {})

    if "error" in choice:
        raw = choice["error"].get("metadata", {}).get("raw", {})
        if raw.get("code") == "insufficient_quota":
            pytest.fail("GPT-5 structured BaseModel choice failed: insufficient quota")
        pytest.fail(f"Error in choice payload: {json.dumps(choice, indent=2)}")

    content = message.get("content", "")
    if not content.strip():
        pytest.fail("GPT-5 returned empty content for structured BaseModel output")

    parsed = SimpleResponse.model_validate_json(content)
    assert "paris" in parsed.answer.lower(), parsed
    assert parsed.confidence >= 0, parsed
