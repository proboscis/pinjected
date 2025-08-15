"""Test GPT-5 with correct parameter names."""

import httpx
import json
import pytest
from pinjected import design, injected
from pinjected.test import injected_pytest


@pytest.mark.asyncio
@injected_pytest(design(openai_config=injected("openai_config__personal")))
async def test_gpt5_with_correct_params(
    openai_config,
    logger,
    /,
):
    """Test GPT-5 directly with max_completion_tokens parameter."""

    if not openai_config or "api_key" not in openai_config:
        logger.error("OpenAI API key not configured")
        pytest.skip("OpenAI API key not available")

    openai_api_key = openai_config["api_key"]

    models = [
        ("gpt-4o", "max_tokens"),  # GPT-4o uses max_tokens
        ("gpt-5-nano", "max_completion_tokens"),  # GPT-5 uses max_completion_tokens
        ("gpt-5", "max_completion_tokens"),
    ]

    async with httpx.AsyncClient() as client:
        for model, param_name in models:
            logger.info(f"\n{'=' * 60}")
            logger.info(f"Testing {model} with {param_name}")
            logger.info(f"{'=' * 60}")

            payload = {
                "model": model,
                "messages": [{"role": "user", "content": "Say hello"}],
                param_name: 10,  # Use correct parameter name
            }

            try:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {openai_api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=30.0,
                )

                if response.status_code == 200:
                    result = response.json()
                    content = result["choices"][0]["message"]["content"]
                    logger.info(f"✅ SUCCESS! Response: {content}")

                    # Log usage for GPT-5
                    if "gpt-5" in model:
                        usage = result.get("usage", {})
                        logger.info(f"Usage: {usage}")
                        if "reasoning_tokens" in usage:
                            logger.info(
                                f"Reasoning tokens: {usage['reasoning_tokens']}"
                            )
                else:
                    error_data = response.json()
                    logger.error(f"❌ ERROR {response.status_code}: {error_data}")

            except Exception as e:
                logger.error(f"❌ Exception: {e}")


@pytest.mark.asyncio
@injected_pytest(design(openrouter_api_key=injected("openrouter_api_key__personal")))
async def test_gpt5_via_openrouter_fixed(
    a_openrouter_post,
    logger,
    /,
):
    """Test GPT-5 via OpenRouter with correct parameter."""

    logger.info("Testing GPT-5 via OpenRouter with max_completion_tokens")

    payload = {
        "model": "openai/gpt-5",
        "messages": [{"role": "user", "content": "Say hello"}],
        "max_completion_tokens": 10,  # Use correct parameter for GPT-5
    }

    try:
        res = await a_openrouter_post(payload)

        if res.get("choices"):
            choice = res["choices"][0]

            # Check for error
            if "error" in choice:
                logger.error(f"Error in choice: {choice['error']}")
            elif "message" in choice:
                content = choice["message"].get("content", "")
                if content:
                    logger.info(f"✅ SUCCESS! Content: {content}")
                else:
                    logger.warning(
                        f"Empty content, response: {json.dumps(res, indent=2)}"
                    )
        else:
            logger.info(f"Response: {json.dumps(res, indent=2)}")

    except Exception as e:
        logger.error(f"Error: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "-x"])
