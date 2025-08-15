"""Test other OpenAI models with BYOK to isolate GPT-5 issue."""

import pytest
from pinjected import design, injected
from pinjected.test import injected_pytest
from pydantic import BaseModel


class SimpleResponse(BaseModel):
    text: str


@pytest.mark.asyncio
@injected_pytest(design(openrouter_api_key=injected("openrouter_api_key__personal")))
async def test_gpt4o_with_byok(
    a_openrouter_chat_completion,
    logger,
    /,
):
    """Test GPT-4o with BYOK setup."""

    logger.info("Testing GPT-4o with BYOK (personal API key)")

    try:
        # Test without response_format first
        result = await a_openrouter_chat_completion(
            prompt="Say hello",
            model="openai/gpt-4o",
            max_tokens=50,
        )
        logger.info(f"✅ GPT-4o works! Result: {result}")

        # Now test with response_format
        result2 = await a_openrouter_chat_completion(
            prompt="Say hello",
            model="openai/gpt-4o",
            response_format=SimpleResponse,
            max_tokens=50,
        )
        logger.info(f"✅ GPT-4o with response_format works! Result: {result2}")
        assert isinstance(result2, SimpleResponse)
        assert result2.text

    except Exception as e:
        logger.error(f"GPT-4o failed: {e}")
        raise


@pytest.mark.asyncio
@injected_pytest(design(openrouter_api_key=injected("openrouter_api_key__personal")))
async def test_gpt4o_mini_with_byok(
    a_openrouter_chat_completion,
    logger,
    /,
):
    """Test GPT-4o-mini with BYOK setup."""

    logger.info("Testing GPT-4o-mini with BYOK (personal API key)")

    try:
        result = await a_openrouter_chat_completion(
            prompt="Say hello",
            model="openai/gpt-4o-mini",
            response_format=SimpleResponse,
            max_tokens=50,
        )
        logger.info(f"✅ GPT-4o-mini with response_format works! Result: {result}")
        assert isinstance(result, SimpleResponse)
        assert result.text

    except Exception as e:
        logger.error(f"GPT-4o-mini failed: {e}")
        raise


@pytest.mark.asyncio
@injected_pytest(design(openrouter_api_key=injected("openrouter_api_key__personal")))
async def test_gpt35_turbo_with_byok(
    a_openrouter_chat_completion,
    logger,
    /,
):
    """Test GPT-3.5-turbo with BYOK setup."""

    logger.info("Testing GPT-3.5-turbo with BYOK (personal API key)")

    try:
        result = await a_openrouter_chat_completion(
            prompt="Say hello",
            model="openai/gpt-3.5-turbo",
            max_tokens=50,
        )
        logger.info(f"✅ GPT-3.5-turbo works! Result: {result}")

    except Exception as e:
        logger.error(f"GPT-3.5-turbo failed: {e}")
        raise


@pytest.mark.asyncio
@injected_pytest
async def test_check_gpt5_actual_status(
    a_openrouter_post,
    logger,
    /,
):
    """Check GPT-5's actual status by calling it directly."""

    # Test different GPT-5 variants
    gpt5_models = [
        "openai/gpt-5",
        "openai/gpt-5-chat",
        "openai/gpt-5-mini",
        "openai/gpt-5-nano",
    ]

    for model in gpt5_models:
        logger.info(f"\nTesting {model}:")

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": "Say hello"}],
            "max_tokens": 10,
        }

        try:
            res = await a_openrouter_post(payload)

            # Check for error in choices
            if res.get("choices") and "error" in res["choices"][0]:
                error = res["choices"][0]["error"]
                logger.warning(f"  Error: {error.get('message', error)}")
                metadata = error.get("metadata", {})
                raw = metadata.get("raw", {})
                if raw:
                    logger.warning(f"  Raw error: {raw}")
            else:
                # Success!
                content = (
                    res.get("choices", [{}])[0].get("message", {}).get("content", "")
                )
                if content:
                    logger.info(f"  ✅ SUCCESS! Content: {content}")
                else:
                    logger.warning(
                        f"  Empty content, finish_reason: {res.get('choices', [{}])[0].get('finish_reason')}"
                    )

        except Exception as e:
            logger.error(f"  Exception: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "-x"])
