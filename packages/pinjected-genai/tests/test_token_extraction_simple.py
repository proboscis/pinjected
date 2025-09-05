"""Simple test to verify token extraction from Gen AI API responses."""

from pinjected import design
from pinjected.test import injected_pytest
from pinjected_genai.image_generation import extract_token_counts_from_usage_metadata
from google.genai.types import (
    GenerateContentResponseUsageMetadata,
    ModalityTokenCount,
    MediaModality,
)

# Empty test design since these are pure function tests
test_di = design()


@injected_pytest(test_di)
def test_extract_token_counts():
    """Test that we can extract modality-specific tokens from API response metadata."""

    # Create mock usage metadata like what the API returns
    usage_metadata = GenerateContentResponseUsageMetadata(
        prompt_token_count=263,
        candidates_token_count=12,
        prompt_tokens_details=[
            ModalityTokenCount(modality=MediaModality.IMAGE, token_count=258),
            ModalityTokenCount(modality=MediaModality.TEXT, token_count=5),
        ],
        candidates_tokens_details=[
            ModalityTokenCount(modality=MediaModality.TEXT, token_count=12),
        ],
    )

    # Extract token counts
    result = extract_token_counts_from_usage_metadata(usage_metadata)

    # Verify extraction worked correctly
    assert result["text_input_tokens"] == 5, (
        f"Expected 5 text input tokens, got {result['text_input_tokens']}"
    )
    assert result["text_output_tokens"] == 12, (
        f"Expected 12 text output tokens, got {result['text_output_tokens']}"
    )
    assert result["image_input_tokens"] == 258, (
        f"Expected 258 image input tokens, got {result['image_input_tokens']}"
    )
    assert result["image_output_tokens"] == 0, (
        f"Expected 0 image output tokens, got {result['image_output_tokens']}"
    )

    print("✅ Token extraction test passed!")
    print(f"Extracted tokens: {result}")


@injected_pytest(test_di)
def test_extract_with_image_output():
    """Test extraction when image output tokens are present."""

    # Create mock with image output tokens
    usage_metadata = GenerateContentResponseUsageMetadata(
        prompt_token_count=10,
        candidates_token_count=1300,
        prompt_tokens_details=[
            ModalityTokenCount(modality=MediaModality.TEXT, token_count=10),
        ],
        candidates_tokens_details=[
            ModalityTokenCount(modality=MediaModality.TEXT, token_count=10),
            ModalityTokenCount(modality=MediaModality.IMAGE, token_count=1290),
        ],
    )

    result = extract_token_counts_from_usage_metadata(usage_metadata)

    assert result["text_input_tokens"] == 10
    assert result["text_output_tokens"] == 10
    assert result["image_input_tokens"] == 0
    assert result["image_output_tokens"] == 1290

    print("✅ Image output token extraction test passed!")
    print(f"Extracted tokens: {result}")


@injected_pytest(test_di)
def test_extract_raises_on_none():
    """Test that extraction raises error on None input."""

    try:
        extract_token_counts_from_usage_metadata(None)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "usage_metadata is None" in str(e)
        print(f"✅ Correctly raised error: {e}")


if __name__ == "__main__":
    test_extract_token_counts()
    test_extract_with_image_output()
    test_extract_raises_on_none()
    print("\n🎉 All tests passed!")
