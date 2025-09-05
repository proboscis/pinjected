"""Test to verify token extraction from API response in image generation functions."""

import pytest
from pinjected import design
from pinjected.test import injected_pytest
from loguru import logger
from PIL import Image
from pinjected_genai.genai_pricing import GenAIModelTable, GenAIState
from pinjected_genai.clients import genai_client


# Test design for dependency injection
def get_test_di():
    """Get test design for dependency injection."""
    # Create a new state dataclass for tracking
    test_state = GenAIState()

    return design(
        logger=logger,
        genai_client=genai_client,
        genai_model_table=GenAIModelTable(),
        genai_state=test_state,
    )


@injected_pytest(get_test_di())
@pytest.mark.asyncio
async def test_describe_image_token_extraction(
    a_describe_image__genai, genai_state, logger, /
):
    """Test that a_describe_image__genai correctly extracts token counts from API response."""
    logger.info("Testing token extraction in a_describe_image__genai...")

    # Create a simple test image
    img = Image.new("RGB", (100, 100), color="red")
    img_path = "/tmp/test_image_token_extraction.png"
    img.save(img_path)

    # Call describe image function
    description = await a_describe_image__genai(
        image_path=img_path,
        prompt="Describe this test image briefly",
        model="gemini-2.5-flash",
    )

    logger.info(f"Description: {description[:100]}...")

    # Check that tokens were extracted (not using estimates)
    # If actual tokens were extracted, we should have text_input_tokens and text_output_tokens
    # as well as image_input_tokens
    logger.info("State after API call:")
    logger.info(f"  Text input tokens: {genai_state.total_text_input_tokens}")
    logger.info(f"  Text output tokens: {genai_state.total_text_output_tokens}")
    logger.info(f"  Image input tokens: {genai_state.total_image_input_tokens}")
    logger.info(f"  Image output tokens: {genai_state.total_image_output_tokens}")
    logger.info(f"  Total cost: ${genai_state.total_cost_usd:.6f}")

    # Verify we got actual token counts
    # Note: Cost might be 0 for gemini-2.5-flash since image inputs are free
    # But we should still track the token counts
    assert genai_state.total_text_input_tokens > 0, (
        "Text input tokens should be greater than 0"
    )
    assert genai_state.total_text_output_tokens > 0, (
        "Text output tokens should be greater than 0"
    )
    assert genai_state.total_image_input_tokens > 0, (
        "Image input tokens should be greater than 0 (we sent an image)"
    )
    assert genai_state.total_image_output_tokens == 0, (
        "Image output tokens should be 0 (no image generated)"
    )

    # Cost should be > 0 due to text tokens even if image input is free
    assert genai_state.total_cost_usd > 0, (
        f"Cost should be > 0 from text tokens (got ${genai_state.total_cost_usd:.6f})"
    )

    # Clean up
    import os

    os.remove(img_path)

    logger.info(
        "✅ Token extraction test passed! Image tokens are being tracked separately from text tokens."
    )
