"""Test to reproduce GPT-5 404 error with response_format and fix."""

import pytest
from pinjected import design, injected
from pinjected.test import injected_pytest
from pydantic import BaseModel


class A(BaseModel):
    random_text: str


@pytest.mark.asyncio
@injected_pytest
async def test_gpt5_404_with_response_format(
    a_openrouter_chat_completion,
    logger,
    /,
):
    """Test that reproduces the 404 error when using GPT-5 with response_format."""

    # Clear the cache to ensure test isolation
    from pinjected_openai.openrouter.util import clear_false_json_claims_cache

    clear_false_json_claims_cache()

    # Try to call GPT-5 with response_format - this should fail with 404 or use fallback
    try:
        result = await a_openrouter_chat_completion(
            prompt="Generate some random text. Include it in a field called 'random_text'.",
            model="openai/gpt-5",
            response_format=A,
            max_tokens=100,
        )
        logger.info(f"Result: {result}")
        # If we get here, either BYOK is configured or fallback worked
        assert isinstance(result, A)
        assert result.random_text
    except RuntimeError as e:
        error_msg = str(e)
        logger.error(f"Got RuntimeError: {error_msg}")

        # Check if this is our improved error message
        if "reports supporting response_format but is not available" in error_msg:
            logger.info("Got improved error message")
            assert "The model requires BYOK" in error_msg
            assert "doesn't actually support structured outputs" in error_msg
            assert "https://openrouter.ai/docs/provider-routing" in error_msg
            logger.info("✅ Improved error message working correctly!")
            # This is expected behavior - test passes
            return
        # Also check for original 404 error
        elif "404" in error_msg and "No endpoints found" in error_msg:
            logger.info("Got original 404 error for GPT-5 without BYOK")
            # This should have been caught by our handler
            raise AssertionError(
                "Should have gotten improved BYOK error message, but got original 404"
            )
        else:
            # Unexpected error, re-raise
            raise


@pytest.mark.asyncio
@injected_pytest(design(openrouter_api_key=injected("openrouter_api_key__personal")))
async def test_gpt5_with_byok(
    a_openrouter_chat_completion,
    logger,
    /,
):
    """Test GPT-5 with personal API key (BYOK setup)."""

    # This test uses personal API key configuration
    logger.info("Testing GPT-5 with BYOK (personal API key)")

    try:
        result = await a_openrouter_chat_completion(
            prompt="Say hello and provide some random text",
            model="openai/gpt-5",
            response_format=A,
            max_tokens=100,
            temperature=0,
        )
        logger.info(f"✅ GPT-5 with BYOK succeeded! Result: {result}")
        assert isinstance(result, A)
        assert result.random_text
        logger.info("GPT-5 works correctly with personal API key configuration!")
    except RuntimeError as e:
        error_msg = str(e)
        # With personal API key, we should get the same comprehensive error message
        if "reports supporting response_format but is not available" in error_msg:
            logger.info("Got expected error for BYOK setup")
            # Check that it mentions the BYOK case
            assert (
                "If you're using a personal/BYOK API key and still seeing this error"
                in error_msg
            )
            assert "may not actually support response_format" in error_msg
            logger.info(
                "✅ Correct error message that acknowledges BYOK is configured!"
            )
            # This is expected - GPT-5 doesn't work even with BYOK
            return
        else:
            # Unexpected error
            logger.error(f"Unexpected error: {error_msg}")
            raise


@pytest.mark.asyncio
@injected_pytest
async def test_gpt5_fallback_without_response_format(
    a_openrouter_chat_completion,
    logger,
    /,
):
    """Test that GPT-5 works without response_format (fallback behavior)."""

    try:
        # Try without response_format - this might work
        result = await a_openrouter_chat_completion(
            prompt="Say hello",
            model="openai/gpt-5",
            max_tokens=50,
            temperature=0,
        )
        logger.info(f"GPT-5 without response_format worked: {result}")
        assert isinstance(result, str)
    except RuntimeError as e:
        if "404" in str(e):
            logger.info("GPT-5 requires BYOK even for basic usage")
            pytest.skip("GPT-5 requires BYOK")
        else:
            raise


@pytest.mark.asyncio
@injected_pytest
async def test_model_with_byok_requirement(
    openrouter_model_table,
    logger,
    /,
):
    """Check if we can detect models that require BYOK."""

    # Check GPT-5 model info
    model = openrouter_model_table.get_model("openai/gpt-5")
    if model:
        logger.info(f"GPT-5 found")
        logger.info(f"Supported parameters: {model.supported_parameters}")
        logger.info(f"Supports JSON: {model.supports_json_output()}")

        # Check if there's any field indicating BYOK requirement
        # This might not exist yet, but would be useful
        if hasattr(model, "requires_byok"):
            logger.info(f"Requires BYOK: {model.requires_byok}")
        else:
            logger.info("No 'requires_byok' field found")

        # Check provider info
        if hasattr(model, "providers"):
            logger.info(f"Providers: {model.providers}")
    else:
        logger.warning("GPT-5 not found in model table")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "-x"])
