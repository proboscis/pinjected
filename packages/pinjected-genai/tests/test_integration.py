"""Integration tests for pinjected-genai that use real Google GenAI API.

These tests assume proper GCP credentials and project configuration are injected.
The user should provide gcp_credentials and gcp_project_id through dependency injection.
"""

import tempfile
from pathlib import Path

import pytest
from pinjected_genai.image_generation import (
    GeneratedImage,
    GenerationResult,
    AGenerateImageProtocol,
)

from pinjected import IProxy, design, injected
from pinjected.test import injected_pytest


@injected_pytest
async def test_gcp_credentials(gcp_credentials):
    assert gcp_credentials is not None


check_gcp_credentials: IProxy = injected("gcp_credentials")


@pytest.mark.integration
@pytest.mark.asyncio
@injected_pytest(design())
async def test_real_generate_single_image(a_generate_image__genai, logger, /):
    """Test generating a single image with real API."""
    logger.info("Starting real image generation test")

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
        logger.info(f"Successfully saved generated image to {tmp_path}")
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    logger.info("Real image generation test completed successfully")


@pytest.mark.integration
@pytest.mark.asyncio
@injected_pytest(design())
async def test_real_describe_image(
    a_describe_image__genai, a_generate_image__genai, genai_client, logger, /
):
    """Test describing an image using real API."""
    logger.info("Starting real image description test")

    # First generate an image to describe
    result = await a_generate_image__genai(
        prompt="A blue square with the number 7 written in white",
        model="gemini-2.5-flash-image-preview",
    )

    # Save the generated image
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
        tmp_path = tmp_file.name

    try:
        result.image.save(tmp_path)
        logger.info(f"Saved test image to {tmp_path}")

        # Now describe the image
        description = await a_describe_image__genai(
            image_path=tmp_path,
            prompt="What shape and number do you see in this image?",
            model="gemini-2.5-flash",
        )

        assert description is not None
        assert len(description) > 0

        # The description should mention a square or shape and possibly the number
        description_lower = description.lower()
        logger.info(f"Image description: {description}")

        # Basic check that we got a meaningful description
        assert any(
            word in description_lower
            for word in ["square", "shape", "blue", "number", "image", "geometric"]
        )

    finally:
        Path(tmp_path).unlink(missing_ok=True)

    logger.info("Real image description test completed successfully")


@pytest.mark.integration
@pytest.mark.asyncio
@injected_pytest(design())
async def test_real_error_handling_invalid_model(
    a_generate_image__genai: AGenerateImageProtocol, logger, /
):
    """Test error handling with invalid model name using real API."""
    logger.info("Testing error handling with invalid model")

    with pytest.raises(Exception) as exc_info:
        await a_generate_image__genai(prompt="test", model="invalid-model-name-xyz")

    # Should get an error about invalid model
    error_message = str(exc_info.value)
    logger.info(f"Received expected error: {error_message}")

    # The error should mention model or not found
    assert (
        "model" in error_message.lower()
        or "not found" in error_message.lower()
        or "invalid" in error_message.lower()
    )


@pytest.mark.integration
@injected_pytest(design())
def test_real_credentials_info(gcp_project_id, gcp_credentials, logger, /):
    """Test that shows which credentials are being used."""
    logger.info(f"Using project: {gcp_project_id}")
    logger.info(f"Credentials type: {type(gcp_credentials).__name__}")

    # Try to get more info about credentials
    if hasattr(gcp_credentials, "service_account_email"):
        logger.info(f"Service account: {gcp_credentials.service_account_email}")
    elif hasattr(gcp_credentials, "client_id"):
        logger.info(f"Client ID: {gcp_credentials.client_id}")

    assert gcp_credentials is not None
    assert gcp_project_id is not None
