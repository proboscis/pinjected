"""Test nano-banana with explicit global endpoint using dependency injection."""

import tempfile
from pathlib import Path

import pytest
from pinjected_genai.image_generation import GeneratedImage, GenerationResult

from pinjected import design, instance
from pinjected.test import injected_pytest


# Override the location to ensure global endpoint
@instance
def genai_location_override() -> str:
    """Force global location for nano-banana tests."""
    return "global"


# Create a design with the override
test_design = design(genai_location=genai_location_override)


@pytest.mark.integration
@pytest.mark.asyncio
@injected_pytest(test_design)
async def test_nano_banana_with_global(a_generate_image__genai, logger, /):
    """Test nano-banana with explicitly set global endpoint."""
    logger.info("Starting nano-banana test with global endpoint")

    # Generate a simple test image
    result = await a_generate_image__genai(
        prompt="A simple red circle on white background, minimalist geometric art",
        model="gemini-2.5-flash-image-preview",
    )

    # Verify result structure
    assert isinstance(result, GenerationResult)
    assert isinstance(result.image, GeneratedImage)

    # Check image data
    image = result.image
    assert image.image_data is not None
    assert len(image.image_data) > 0
    assert image.mime_type in ["image/png", "image/jpeg"]
    assert (
        image.prompt_used
        == "A simple red circle on white background, minimalist geometric art"
    )

    # Verify we can save the image
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
        tmp_path = tmp_file.name

    try:
        image.save(tmp_path)
        assert Path(tmp_path).exists()
        assert Path(tmp_path).stat().st_size > 0
        logger.info(f"Successfully saved generated nano-banana image to {tmp_path}")
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    logger.info("Nano-banana test completed successfully")
