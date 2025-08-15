"""Test sending max_completion_tokens directly to OpenRouter."""

import pytest
from pinjected import design, injected
from pinjected.test import injected_pytest
import json


@pytest.mark.asyncio
@injected_pytest(design(openrouter_api_key=injected("openrouter_api_key__personal")))
async def test_direct_max_completion_tokens(
    a_openrouter_post,
    logger,
    /,
):
    """Test if OpenRouter passes through max_completion_tokens parameter."""

    models = [
        ("openai/gpt-4o", {"max_tokens": 10}),  # Control - should work
        ("openai/gpt-5-nano", {"max_tokens": 20}),  # What OpenRouter expects
        ("openai/gpt-5-nano", {"max_completion_tokens": 20}),  # What OpenAI expects
        ("openai/gpt-5-nano", {"max_tokens": 20, "max_completion_tokens": 20}),  # Both
    ]

    for model, params in models:
        logger.info(f"\n{'=' * 60}")
        logger.info(f"Testing {model} with params: {params}")
        logger.info(f"{'=' * 60}")

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": "Say hello"}],
            **params,
        }

        try:
            res = await a_openrouter_post(payload)

            if res.get("choices"):
                choice = res["choices"][0]

                if "error" in choice:
                    error = choice["error"]
                    logger.error(f"Error: {error.get('message', error)}")

                    # Check raw error from provider
                    if "metadata" in error and "raw" in error["metadata"]:
                        raw = json.loads(error["metadata"]["raw"])
                        if "error" in raw:
                            logger.error(
                                f"Provider error param: {raw['error'].get('param')}"
                            )
                            logger.error(
                                f"Provider error message: {raw['error'].get('message')}"
                            )
                elif "message" in choice:
                    content = choice["message"].get("content", "")
                    if content:
                        logger.info(f"✅ SUCCESS with params {params}!")
                    else:
                        logger.warning(f"Empty content")
            else:
                logger.error(f"Unexpected response: {json.dumps(res, indent=2)}")

        except Exception as e:
            logger.error(f"Exception: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "-x"])
