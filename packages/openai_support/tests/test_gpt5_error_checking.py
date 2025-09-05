"""Check JSON errors from both OpenAI and OpenRouter API responses."""

import httpx
import json
import pytest
from pinjected import design, injected
from pinjected.test import injected_pytest
from packages.openai_support.conftest import apikey_skip_if_needed

apikey_skip_if_needed()


@pytest.mark.asyncio
@injected_pytest(design(openai_config=injected("openai_config__personal")))
async def test_gpt5_direct_openai_error_checking(
    openai_config,
    logger,
    /,
):
    """Check JSON errors from direct OpenAI API."""

    if not openai_config or "api_key" not in openai_config:
        logger.error("OpenAI API key not configured")
        pytest.skip("OpenAI API key not available")

    openai_api_key = openai_config["api_key"]

    logger.info("\n" + "=" * 80)
    logger.info("CHECKING OPENAI API ERRORS")
    logger.info("=" * 80)

    # Test 1: GPT-5 with wrong parameter (should error)
    logger.info("\n1. Testing GPT-5 with max_tokens (should error):")
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {openai_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "gpt-5-nano",
                "messages": [{"role": "user", "content": "Hello"}],
                "max_tokens": 50,  # Wrong parameter for GPT-5
            },
            timeout=30.0,
        )

        data = response.json()
        if "error" in data:
            error = data["error"]
            logger.error(f"✅ Expected error found:")
            logger.error(f"  - Message: {error.get('message')}")
            logger.error(f"  - Type: {error.get('type')}")
            logger.error(f"  - Code: {error.get('code')}")
            logger.error(f"  - Param: {error.get('param')}")
        else:
            logger.warning("No error in response (unexpected)")
            logger.info(f"Response: {json.dumps(data, indent=2)}")

        # Test 2: GPT-5 with correct parameter - must return non-empty content
        logger.info(
            "\n2. Testing GPT-5 with max_completion_tokens (should return non-empty):"
        )
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {openai_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "gpt-5-nano",
                "messages": [
                    {"role": "user", "content": "Say hello in exactly 3 words"}
                ],
                "max_completion_tokens": 10000,  # Give GPT-5 plenty of tokens for reasoning + output
            },
            timeout=30.0,
        )

        data = response.json()
        if "error" in data:
            error = data["error"]
            logger.error(f"❌ Unexpected error:")
            logger.error(f"  - Message: {error.get('message')}")
            logger.error(f"  - Type: {error.get('type')}")
            logger.error(f"  - Code: {error.get('code')}")
            pytest.fail(f"GPT-5 returned error: {error.get('message')}")
        elif data.get("choices"):
            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})

            # Assert that content is not empty
            assert content and content.strip(), (
                f"GPT-5 returned empty content! Usage: {usage}"
            )

            logger.success(f"✅ Success! Response: '{content}'")
            logger.info(f"   Usage: {usage}")
            if "reasoning_tokens" in usage:
                logger.info(
                    f"   🎯 GPT-5 confirmed (reasoning_tokens: {usage['reasoning_tokens']})"
                )
        else:
            logger.warning(f"Unexpected response: {json.dumps(data, indent=2)}")
            pytest.fail("GPT-5 did not return expected response structure")


@pytest.mark.asyncio
@injected_pytest(design(openrouter_api_key=injected("openrouter_api_key__personal")))
async def test_gpt5_openrouter_error_checking(
    a_openrouter_post,
    logger,
    /,
):
    """Check JSON errors from OpenRouter API."""

    logger.info("\n" + "=" * 80)
    logger.info("CHECKING OPENROUTER API ERRORS")
    logger.info("=" * 80)

    # Test with raw API call to see full error structure
    logger.info("\n1. Testing GPT-5 through OpenRouter (raw):")

    res = await a_openrouter_post(
        {
            "model": "openai/gpt-5-nano",
            "messages": [{"role": "user", "content": "Say hello"}],
            "max_tokens": 10000,  # This should be transformed by our fix to max_completion_tokens
        }
    )

    logger.info(f"\nFull response structure: {json.dumps(res, indent=2)}")

    # Check for top-level error first
    if "error" in res:
        error_msg = res["error"]
        logger.error(f"❌ Top-level error: {error_msg}")
        pytest.fail(f"OpenRouter returned top-level error: {error_msg}")

    # Then check for choices
    if "choices" not in res or not res["choices"]:
        logger.error(f"❌ No choices in response")
        pytest.fail(f"OpenRouter returned no choices: {json.dumps(res, indent=2)}")

    choice = res["choices"][0]

    # Check for error in choice
    if "error" in choice:
        error = choice["error"]
        logger.error(f"\n❌ Error in choice:")
        logger.error(f"  - Message: {error.get('message')}")
        logger.error(f"  - Code: {error.get('code')}")

        # Check metadata for OpenAI error details
        if "metadata" in error and "raw" in error["metadata"]:
            raw = error["metadata"]["raw"]
            if isinstance(raw, str):
                from contextlib import suppress

                with suppress(Exception):
                    raw = json.loads(raw)

            if isinstance(raw, dict) and "error" in raw:
                openai_error = raw["error"]
                logger.error(f"\n  OpenAI backend error:")
                logger.error(f"    - Message: {openai_error.get('message')}")
                logger.error(f"    - Type: {openai_error.get('type')}")
                logger.error(f"    - Code: {openai_error.get('code')}")

        pytest.fail(f"OpenRouter returned error in choice: {error.get('message')}")

    # Only access message content after confirming no errors
    if "message" not in choice:
        logger.error(f"❌ No message in choice")
        pytest.fail(f"OpenRouter choice has no message: {json.dumps(choice, indent=2)}")

    content = choice["message"].get("content", "")

    # Assert that content is not empty for GPT-5
    assert content and content.strip(), (
        f"GPT-5 through OpenRouter returned empty content! Finish reason: {choice.get('finish_reason')}, Usage: {res.get('usage')}"
    )

    logger.success(f"✅ Success! Content: '{content}'")
    if "usage" in res:
        logger.info(f"   Usage: {res['usage']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "-x"])
