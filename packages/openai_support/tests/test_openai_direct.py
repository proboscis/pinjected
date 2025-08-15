"""Test OpenAI API directly to isolate if the issue is with OpenAI or OpenRouter."""

import httpx
import pytest
from pinjected import design, injected
from pinjected.test import injected_pytest


@pytest.mark.asyncio
@injected_pytest(design(openai_config=injected("openai_config__personal")))
async def test_openai_direct(
    openai_config,
    logger,
    /,
):
    """Test GPT-5 directly via OpenAI API."""

    if not openai_config or "api_key" not in openai_config:
        logger.error("OpenAI API key not configured in openai_config__personal")
        pytest.skip("OpenAI API key not available")

    openai_api_key = openai_config["api_key"]

    logger.info("Testing direct OpenAI API access...")

    # Test different models
    models = [
        "gpt-4o",  # Should work if account is active
        "gpt-5-nano",  # Cheapest GPT-5 variant
        "gpt-5-mini",  # Mid-tier GPT-5
        "gpt-5",  # Full GPT-5
    ]

    async with httpx.AsyncClient() as client:
        for model in models:
            logger.info(f"\nTesting {model}:")

            payload = {
                "model": model,
                "messages": [{"role": "user", "content": "Say hello"}],
                "max_tokens": 10,
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
                    logger.info(f"  ✅ SUCCESS! Response: {content}")
                else:
                    error_data = response.json()
                    error_msg = error_data.get("error", {}).get(
                        "message", str(error_data)
                    )
                    error_code = error_data.get("error", {}).get("code", "")

                    if "insufficient_quota" in str(error_code):
                        logger.error(f"  ❌ QUOTA ERROR: {error_msg}")
                    elif response.status_code == 404:
                        logger.warning(f"  ⚠️ Model not found: {error_msg}")
                    else:
                        logger.error(f"  ❌ ERROR {response.status_code}: {error_msg}")

            except Exception as e:
                logger.error(f"  ❌ Exception: {e}")

    # Also check account status
    logger.info("\n\nChecking OpenAI account status:")
    async with httpx.AsyncClient() as client:
        try:
            # Check usage/billing endpoint
            response = await client.get(
                "https://api.openai.com/v1/models",
                headers={
                    "Authorization": f"Bearer {openai_api_key}",
                },
                timeout=30.0,
            )

            if response.status_code == 200:
                models_data = response.json()
                gpt5_models = [
                    m
                    for m in models_data.get("data", [])
                    if "gpt-5" in m.get("id", "").lower()
                ]
                if gpt5_models:
                    logger.info(f"  ✅ Found {len(gpt5_models)} GPT-5 models available")
                    for m in gpt5_models[:3]:  # Show first 3
                        logger.info(f"    - {m['id']}")
                else:
                    logger.warning("  ⚠️ No GPT-5 models found in available models list")
            else:
                logger.error(f"  ❌ Could not fetch models: {response.status_code}")

        except Exception as e:
            logger.error(f"  ❌ Error checking account: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "-x"])
