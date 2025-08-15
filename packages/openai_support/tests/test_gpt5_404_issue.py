"""Test to reproduce GPT-5 404 error with response_format and fix."""

import pytest
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

    # Try to call GPT-5 with response_format - this should fail with 404
    try:
        result = await a_openrouter_chat_completion(
            prompt="hello",
            model="openai/gpt-5",
            response_format=A,
        )
        logger.info(f"Result: {result}")
        # If we get here, GPT-5 is configured with BYOK
        assert isinstance(result, A)
    except RuntimeError as e:
        error_msg = str(e)
        logger.error(f"Got RuntimeError: {error_msg}")

        # Check if this is our improved error message
        if "requires BYOK" in error_msg:
            logger.info("Got improved BYOK error message")
            assert (
                "Model openai/gpt-5 supports response_format but requires BYOK"
                in error_msg
            )
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
