"""Test GPT-5 fallback mechanism for false JSON support claims."""

import pytest
from pinjected.test import injected_pytest
from pydantic import BaseModel


class ResponseModel(BaseModel):
    """Response model for testing."""

    message: str
    sentiment: str


@pytest.mark.asyncio
@injected_pytest
async def test_gpt5_fallback_on_404(
    a_openrouter_chat_completion,
    logger,
    /,
):
    """Test that models correctly fall back when they falsely claim JSON support."""

    # Clear the cache to ensure test isolation
    from pinjected_openai.openrouter.util import clear_false_json_claims_cache

    clear_false_json_claims_cache()

    # First call - should detect false claim and fallback
    logger.info("Testing model with response_format - expecting fallback")

    try:
        result = await a_openrouter_chat_completion(
            prompt="Analyze this message: 'I love sunny days!' Return with message and sentiment fields.",
            model="openai/gpt-5",
            response_format=ResponseModel,
            max_tokens=100,
            temperature=0,
        )

        # If we get here, the fallback worked
        logger.info(f"✅ Fallback successful! Result: {result}")
        assert isinstance(result, ResponseModel)
        assert result.message
        assert result.sentiment
        logger.info(f"Message: {result.message}")
        logger.info(f"Sentiment: {result.sentiment}")

    except RuntimeError as e:
        # If GPT-5 truly isn't available (even without JSON), that's ok
        if "404" in str(e):
            logger.info("GPT-5 not available even for basic usage")
            pytest.skip("GPT-5 requires BYOK or isn't available")
        else:
            raise


@pytest.mark.asyncio
@injected_pytest
async def test_cached_false_claim(
    a_openrouter_chat_completion,
    logger,
    /,
):
    """Test that the cache remembers models with false JSON claims within a session."""

    # Import the cache to check it
    from pinjected_openai.openrouter.util import _models_with_false_json_claims

    logger.info(f"Current cache of false claims: {_models_with_false_json_claims}")

    # First call - should add to cache if not already there
    try:
        result = await a_openrouter_chat_completion(
            prompt="Analyze: 'Hello world!' Return with message and sentiment fields.",
            model="openai/gpt-5",
            response_format=ResponseModel,
            max_tokens=50,
            temperature=0,
        )
        logger.info(f"First call result: {result}")
        assert isinstance(result, ResponseModel)
        assert result.message
        assert result.sentiment
    except RuntimeError as e:
        if "404" in str(e):
            logger.info("GPT-5 not available even for basic usage")
            pytest.skip("GPT-5 not available")

    # Check cache after first call
    logger.info(f"Cache after first call: {_models_with_false_json_claims}")
    assert "openai/gpt-5" in _models_with_false_json_claims, (
        "GPT-5 should be in cache after first 404"
    )

    # Second call - should immediately use fallback without trying JSON
    try:
        result = await a_openrouter_chat_completion(
            prompt="Analyze: 'What a wonderful day!' Return with message and sentiment fields.",
            model="openai/gpt-5",
            response_format=ResponseModel,
            max_tokens=50,
            temperature=0,
        )
        logger.info(f"Second call (using cache) result: {result}")
        assert isinstance(result, ResponseModel)
        assert result.message
        assert result.sentiment
        logger.info("✅ Cache worked - immediate fallback on second call")
    except RuntimeError as e:
        if "404" in str(e):
            logger.info("GPT-5 not available")
            pytest.skip("GPT-5 not available")


@pytest.mark.asyncio
@injected_pytest
async def test_working_model_not_affected(
    a_openrouter_chat_completion,
    logger,
    /,
):
    """Test that working models (like gpt-4o-mini) still use proper JSON mode."""

    result = await a_openrouter_chat_completion(
        prompt="Say hello. Return with message and sentiment fields.",
        model="openai/gpt-4o-mini",
        response_format=ResponseModel,
        max_tokens=50,
        temperature=0,
    )

    logger.info(f"✅ Working model still uses JSON mode: {result}")
    assert isinstance(result, ResponseModel)
    assert result.message
    assert result.sentiment


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "-x"])
