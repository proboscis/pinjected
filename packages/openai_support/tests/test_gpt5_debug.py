"""Debug GPT-5 access issue with detailed logging."""

import pytest
from pinjected import design, injected
from pinjected.test import injected_pytest
import json


@pytest.mark.asyncio
@injected_pytest(design(openrouter_api_key=injected("openrouter_api_key__personal")))
async def test_gpt5_raw_response(
    a_openrouter_post,
    logger,
    /,
):
    """Get raw response from GPT-5 to see exact error details."""

    models_to_test = [
        "openai/gpt-4o",  # Control - should work
        "openai/gpt-5-nano",  # Cheapest GPT-5
        "openai/gpt-5",  # Full GPT-5
    ]

    for model in models_to_test:
        logger.info(f"\n{'=' * 60}")
        logger.info(f"Testing {model}")
        logger.info(f"{'=' * 60}")

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": "Say hello"}],
            "max_tokens": 10,
            "temperature": 0,
        }

        try:
            res = await a_openrouter_post(payload)

            # Log full response
            logger.info(f"Full response:\n{json.dumps(res, indent=2)}")

            # Check for errors in different places
            if "error" in res:
                logger.error(f"Top-level error: {res['error']}")

            if res.get("choices"):
                choice = res["choices"][0]

                # Check for error in choice
                if "error" in choice:
                    error = choice["error"]
                    logger.error(f"Error in choice: {error}")

                    # Extract detailed error info
                    if "metadata" in error:
                        metadata = error["metadata"]
                        if "raw" in metadata:
                            raw = metadata["raw"]
                            logger.error(f"Raw error details: {raw}")

                            # Check specific error codes
                            if raw.get("code") == "insufficient_quota":
                                logger.error(
                                    "❌ INSUFFICIENT QUOTA - OpenAI key has no credits"
                                )
                            elif raw.get("code") == "model_not_found":
                                logger.error(
                                    "❌ MODEL NOT FOUND - GPT-5 not available on this account"
                                )

                    # Check error code
                    if error.get("code") == 502:
                        logger.error("❌ Provider error (502) - OpenAI backend issue")
                    elif error.get("code") == 404:
                        logger.error(
                            "❌ Not found (404) - Model or endpoint not available"
                        )

                # Check for actual content
                if "message" in choice:
                    content = choice["message"].get("content", "")
                    if content:
                        logger.info(f"✅ SUCCESS! Content: {content}")
                    else:
                        logger.warning("⚠️ Empty content in response")
                        finish_reason = choice.get("finish_reason", "unknown")
                        logger.warning(f"Finish reason: {finish_reason}")

        except Exception as e:
            logger.error(f"❌ Exception calling {model}: {e}")
            import traceback

            logger.error(traceback.format_exc())


@pytest.mark.asyncio
@injected_pytest(design(openrouter_api_key=injected("openrouter_api_key__personal")))
async def test_check_openrouter_key_info(
    openrouter_api_key,
    logger,
    /,
):
    """Check OpenRouter API key configuration."""

    if not openrouter_api_key:
        logger.error("No OpenRouter API key configured")
        return

    # Log key info (safely, only first/last few chars)
    if len(openrouter_api_key) > 10:
        safe_key = f"{openrouter_api_key[:4]}...{openrouter_api_key[-4:]}"
        logger.info(f"OpenRouter API key configured: {safe_key}")
    else:
        logger.info("OpenRouter API key configured but too short")

    # Check if it's the personal key by looking at the prefix
    if openrouter_api_key.startswith("sk-or-"):
        logger.info("✅ Using OpenRouter API key format")
    else:
        logger.warning("⚠️ Unexpected API key format")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "-x"])
