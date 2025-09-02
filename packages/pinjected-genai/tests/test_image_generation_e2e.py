import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch, MagicMock

import pytest
from google.auth.credentials import Credentials
from google import genai
from pinjected_genai.image_generation import (
    GeneratedImage,
    GenerationResult,
)

from pinjected import design
from pinjected.test import injected_pytest


# Mock response data
def create_mock_image_response(text_parts=None, image_count=1):
    """Create a mock response with text and/or images."""
    parts = []

    if text_parts:
        for text in text_parts:
            part = Mock()
            part.text = text
            part.inline_data = None
            parts.append(part)

    for i in range(image_count):
        part = Mock()
        part.text = None
        part.inline_data = Mock()
        part.inline_data.mime_type = "image/png"
        part.inline_data.data = b"fake_image_data_%d" % i
        parts.append(part)

    # Create mock content
    content = Mock()
    content.parts = parts

    # Create mock candidate
    candidate = Mock()
    candidate.content = content

    # Create mock response
    response = Mock()
    response.candidates = [candidate]
    response.text = "\n".join(text_parts) if text_parts else None

    return response


# Create a mock genai.Client
def create_mock_genai_client():
    """Create a mock genai.Client."""
    mock_client = MagicMock(spec=genai.Client)
    mock_models = MagicMock()
    mock_models.generate_content = AsyncMock()
    mock_client.aio.models = mock_models
    return mock_client


# Mock credentials and test design
mock_credentials = Mock(spec=Credentials)


def get_test_di():
    """Create a fresh test design with a new mock client for each test."""
    mock_genai_client = create_mock_genai_client()

    # Import the functions we need to test
    from pinjected_genai.image_generation import (
        a_generate_image__genai,
        a_describe_image__genai,
        a_edit_image__genai,
    )

    # Patch genai.Client to avoid actual initialization
    with patch("pinjected_genai.clients.genai.Client", return_value=mock_genai_client):
        return design(
            gcp_project_id="test-project",
            gcp_credentials=mock_credentials,
            genai_location="global",
            genai_client=mock_genai_client,  # Inject the mock client directly
            # Add the functions to the design
            a_generate_image__genai=a_generate_image__genai,
            a_describe_image__genai=a_describe_image__genai,
            a_edit_image__genai=a_edit_image__genai,
        )


# Create the test design
test_di = get_test_di()


@injected_pytest(get_test_di())
@pytest.mark.asyncio
async def test_a_generate_image_single(
    a_generate_image__genai, genai_client, logger, /
):
    """Test generating a single image."""
    # Setup mock response
    genai_client.aio.models.generate_content.return_value = create_mock_image_response(
        image_count=1
    )

    # Call the injected function with non-injected parameters only
    result = await a_generate_image__genai(
        prompt="A cute baby turtle", model="gemini-2.5-flash-image-preview"
    )

    # Verify the function was called
    genai_client.aio.models.generate_content.assert_called_once()

    # Verify result structure
    assert isinstance(result, GenerationResult)
    assert result.image.image_data == b"fake_image_data_0"
    assert result.image.mime_type == "image/png"
    assert result.image.prompt_used == "A cute baby turtle"
    assert result.model_used == "gemini-2.5-flash-image-preview"


@injected_pytest(get_test_di())
@pytest.mark.asyncio
async def test_a_generate_image_with_text(
    a_generate_image__genai, genai_client, logger, /
):
    """Test generating image with text response."""
    # Setup mock response with both text and image
    genai_client.aio.models.generate_content.return_value = create_mock_image_response(
        text_parts=["Here's your image:", "A beautiful mountain landscape"],
        image_count=1,
    )

    # Call the injected function
    result = await a_generate_image__genai(
        prompt="Generate a mountain landscape", model="gemini-2.5-flash-image-preview"
    )

    # Verify result contains both text and image
    assert isinstance(result, GenerationResult)
    assert result.text == "Here's your image:\nA beautiful mountain landscape"
    assert result.image.image_data == b"fake_image_data_0"


@injected_pytest(get_test_di())
@pytest.mark.asyncio
async def test_a_generate_image_no_images(
    a_generate_image__genai, genai_client, logger, /
):
    """Test handling when no images are generated - should raise ValueError."""
    # Setup mock response with no images
    genai_client.aio.models.generate_content.return_value = create_mock_image_response(
        text_parts=["Sorry, I couldn't generate an image"], image_count=0
    )

    # Call should raise ValueError when no image is returned
    with pytest.raises(ValueError, match="Model .* did not return any image"):
        await a_generate_image__genai(
            prompt="Generate something impossible",
            model="gemini-2.5-flash-image-preview",
        )


@injected_pytest(get_test_di())
@pytest.mark.asyncio
async def test_a_generate_image_error_handling(
    a_generate_image__genai, genai_client, logger, /
):
    """Test error handling during image generation."""
    # Setup mock to raise an exception
    genai_client.aio.models.generate_content.side_effect = Exception(
        "API Error: Rate limit exceeded"
    )

    # Call should raise the exception
    with pytest.raises(Exception, match="API Error: Rate limit exceeded"):
        await a_generate_image__genai(
            prompt="Test prompt", model="gemini-2.5-flash-image-preview"
        )


@injected_pytest(get_test_di())
@pytest.mark.asyncio
async def test_a_describe_image(a_describe_image__genai, genai_client, logger, /):
    """Test describing an image."""
    # Create a temporary test image
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
        tmp_path = tmp_file.name
        # Write a minimal valid PNG (1x1 pixel, red)
        tmp_file.write(
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0\x00\x00\x03\x01\x01\x00\xc9\xfe\x92\xef\x00\x00\x00\x00IEND\xaeB`\x82"
        )

    try:
        # Setup mock response
        mock_response = Mock()
        mock_response.text = "This is a test image with geometric shapes"
        genai_client.aio.models.generate_content.return_value = mock_response

        # Call the describe function
        description = await a_describe_image__genai(
            image_path=tmp_path,
            prompt="What do you see in this image?",
            model="gemini-2.5-flash",
        )

        # Verify the response
        assert description == "This is a test image with geometric shapes"

        # Verify the function was called
        genai_client.aio.models.generate_content.assert_called_once()

    finally:
        # Clean up the temp file
        Path(tmp_path).unlink(missing_ok=True)


@injected_pytest(get_test_di())
@pytest.mark.asyncio
async def test_a_describe_image_no_prompt(
    a_describe_image__genai, genai_client, logger, /
):
    """Test describing an image with default prompt."""
    # Create a temporary test image
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
        tmp_path = tmp_file.name
        # Write a minimal valid PNG (1x1 pixel, red)
        tmp_file.write(
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0\x00\x00\x03\x01\x01\x00\xc9\xfe\x92\xef\x00\x00\x00\x00IEND\xaeB`\x82"
        )

    try:
        # Setup mock response
        mock_response = Mock()
        mock_response.text = "A simple geometric pattern"
        genai_client.aio.models.generate_content.return_value = mock_response

        # Call the describe function without custom prompt
        description = await a_describe_image__genai(
            image_path=tmp_path, model="gemini-2.5-flash"
        )

        # Verify the response
        assert description == "A simple geometric pattern"

    finally:
        # Clean up the temp file
        Path(tmp_path).unlink(missing_ok=True)


@injected_pytest(get_test_di())
@pytest.mark.asyncio
async def test_generated_image_methods(logger, /):
    """Test GeneratedImage helper methods."""
    # Create a test GeneratedImage
    image = GeneratedImage(
        image_data=b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x01\x00\x00\x00\x007n\xf9$\x00\x00\x00\nIDAT\x08\x1dc\xf8\x00\x00\x00\x01\x00\x01UU\x86\x18\x00\x00\x00\x00IEND\xaeB`\x82",
        mime_type="image/png",
        prompt_used="Test prompt",
    )

    # Test to_base64
    base64_str = image.to_base64()
    assert isinstance(base64_str, str)
    assert len(base64_str) > 0

    # Test save method
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
        tmp_path = tmp_file.name

    try:
        image.save(tmp_path)
        assert Path(tmp_path).exists()
        assert Path(tmp_path).stat().st_size > 0
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@injected_pytest(get_test_di())
@pytest.mark.asyncio
async def test_a_edit_image(a_edit_image__genai, genai_client, logger, /):
    """Test editing/generating an image with input images."""
    from PIL import Image as PILImage

    # Create test input images
    img1 = PILImage.new("RGB", (100, 100), color="red")
    img2 = PILImage.new("RGB", (100, 100), color="blue")

    # Setup mock response
    genai_client.aio.models.generate_content.return_value = create_mock_image_response(
        text_parts=["Here's your edited image"], image_count=1
    )

    # Test with multiple input images
    result = await a_edit_image__genai(
        input_images=[img1, img2],
        prompt="Combine these images into one",
        model="gemini-2.5-flash-image-preview",
    )

    # Verify result
    assert isinstance(result, GenerationResult)
    assert result.image.image_data == b"fake_image_data_0"
    assert result.image.mime_type == "image/png"
    assert "Edit:" in result.image.prompt_used
    assert result.model_used == "gemini-2.5-flash-image-preview"

    # Test with empty input images list
    result = await a_edit_image__genai(
        input_images=[],
        prompt="Generate a new image from scratch",
        model="gemini-2.5-flash-image-preview",
    )

    # Verify result
    assert isinstance(result, GenerationResult)
    assert result.image.image_data == b"fake_image_data_0"


@injected_pytest(get_test_di())
@pytest.mark.asyncio
async def test_a_edit_image_no_images_returned(
    a_edit_image__genai, genai_client, logger, /
):
    """Test that edit image raises ValueError when no image is returned."""
    from PIL import Image as PILImage

    # Create test input image
    img = PILImage.new("RGB", (100, 100), color="green")

    # Setup mock response with no images
    genai_client.aio.models.generate_content.return_value = create_mock_image_response(
        text_parts=["Failed to edit"], image_count=0
    )

    # Should raise ValueError
    with pytest.raises(ValueError, match="Model .* did not return any edited image"):
        await a_edit_image__genai(
            input_images=[img],
            prompt="Edit this image",
            model="gemini-2.5-flash-image-preview",
        )
