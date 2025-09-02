"""Visual verification tests for generated images.

These tests are skipped by default but can be run manually to visually verify
the generated images using matplotlib.

To run these tests:
    pytest tests/test_visual_verification.py::test_visual_single_image -xvs

Or run all visual tests:
    pytest tests/test_visual_verification.py -xvs
"""

import tempfile
from pathlib import Path

import matplotlib
import pytest
from pinjected_genai.image_generation import (
    a_generate_image__genai,
    a_edit_image__genai,
    a_describe_image__genai,
)

# Use non-interactive backend by default to avoid display issues
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from pinjected import design, instance
from pinjected.test import injected_pytest

# Import the image generation modules to ensure they're available


@instance
def run_visual_tests() -> bool:
    """Configuration to control whether visual tests should run.

    Override this in your test by injecting run_visual_tests=True
    """
    return False


# Custom marker for visual tests - manually run these specific tests
@pytest.mark.visual
@pytest.mark.integration
@pytest.mark.asyncio
@injected_pytest(design())
async def test_visual_single_image(a_generate_image__genai, logger, /):
    """Generate a single image and display it for visual verification."""
    logger.info("Starting visual verification test for single image")

    # Generate a test image with a clear, verifiable prompt
    result = await a_generate_image__genai(
        prompt="A red circle on the left, a blue square in the center, and a green triangle on the right, all on a white background",
        model="gemini-2.5-flash-image-preview",
    )

    assert result.image is not None

    # Convert to PIL image and display
    img = result.image.to_pil_image()

    # Create figure
    plt.figure(figsize=(10, 8))
    plt.imshow(img)
    plt.axis("off")
    plt.title(f"Generated Image\nPrompt: {result.image.prompt_used[:100]}...")
    plt.tight_layout()

    # Save to temp file for inspection
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        plt.savefig(tmp.name, dpi=150, bbox_inches="tight")
        logger.info(f"Saved visualization to: {tmp.name}")

    # Show the plot (will display if running interactively)
    plt.show()

    logger.info("Visual verification complete - check the displayed image")


@pytest.mark.visual
@pytest.mark.integration
@pytest.mark.asyncio
@injected_pytest(design())
async def test_visual_different_prompts(a_generate_image__genai, logger, /):
    """Generate images with different prompts and display them for comparison."""
    logger.info("Starting visual verification test with different prompts")

    prompts = [
        "A minimalist landscape with mountains and a sunset",
        "An abstract composition with flowing lines and vibrant colors",
        "A futuristic cityscape with neon lights",
        "A peaceful garden with flowers and butterflies",
    ]

    images = []

    # Generate images for each prompt
    for prompt in prompts:
        logger.info(f"Generating image for: {prompt}")
        result = await a_generate_image__genai(
            prompt=prompt, model="gemini-2.5-flash-image-preview"
        )
        assert result.image is not None
        images.append((prompt, result.image))

    # Create a 2x2 grid
    fig, axes = plt.subplots(2, 2, figsize=(14, 14))
    fig.suptitle("Generated Images with Different Prompts", fontsize=16)

    for ax, (prompt, img_data) in zip(axes.flat, images):
        img = img_data.to_pil_image()
        ax.imshow(img)
        ax.axis("off")
        # Wrap long prompts
        title = prompt if len(prompt) <= 40 else prompt[:37] + "..."
        ax.set_title(title, fontsize=10)

    plt.tight_layout()

    # Save to temp file for inspection
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        plt.savefig(tmp.name, dpi=150, bbox_inches="tight")
        logger.info(f"Saved visualization to: {tmp.name}")

    # Show the plot
    plt.show()

    logger.info("Visual verification complete - compare the different generated images")


@pytest.mark.visual
@pytest.mark.integration
@pytest.mark.asyncio
@injected_pytest(design())
async def test_visual_describe_generated_image(
    a_generate_image__genai, a_describe_image__genai, logger, /
):
    """Generate an image, save it, then describe it and display both."""
    logger.info("Starting visual verification test for image description")

    # Generate an image
    prompt = "A robot playing chess with a cat in a library"
    result = await a_generate_image__genai(
        prompt=prompt, model="gemini-2.5-flash-image-preview"
    )

    assert result.image is not None

    # Save the image temporarily
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        result.image.save(tmp.name)
        tmp_path = tmp.name

    try:
        # Describe the image
        description = await a_describe_image__genai(
            image_path=tmp_path,
            prompt="Describe what you see in this image in detail. What is happening in the scene?",
            model="gemini-2.5-flash",
        )

        # Create visualization
        plt.figure(figsize=(14, 8))

        # Image on the left
        ax1 = plt.subplot(1, 2, 1)
        img = result.image.to_pil_image()
        ax1.imshow(img)
        ax1.axis("off")
        ax1.set_title(f"Generated Image\nPrompt: {prompt[:50]}...", fontsize=12)

        # Description on the right
        ax2 = plt.subplot(1, 2, 2)
        ax2.axis("off")

        # Format description text
        import textwrap

        wrapped_desc = textwrap.fill(description[:600], width=50)
        if len(description) > 600:
            wrapped_desc += "\n\n[... truncated for display ...]"

        ax2.text(
            0.05,
            0.95,
            "AI Description:",
            fontsize=14,
            fontweight="bold",
            transform=ax2.transAxes,
            verticalalignment="top",
        )
        ax2.text(
            0.05,
            0.85,
            wrapped_desc,
            fontsize=10,
            transform=ax2.transAxes,
            verticalalignment="top",
            wrap=True,
        )

        plt.suptitle("Image Generation and Description Test", fontsize=16)
        plt.tight_layout()

        # Save visualization
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as vis_tmp:
            plt.savefig(vis_tmp.name, dpi=150, bbox_inches="tight")
            logger.info(f"Saved visualization to: {vis_tmp.name}")

        # Show the plot
        plt.show()

        logger.info(
            "Visual verification complete - check if description matches the image"
        )

    finally:
        # Clean up temp file
        Path(tmp_path).unlink(missing_ok=True)


@pytest.mark.visual
@pytest.mark.integration
@pytest.mark.asyncio
@injected_pytest(design())
async def test_visual_aspect_ratios(a_generate_image__genai, logger, /):
    """Test generating images with different aspect ratios (if supported)."""
    logger.info("Starting visual verification test for aspect ratios")

    # Note: Current implementation uses 1:1 aspect ratio by default
    # This test generates multiple images to show consistency

    prompts_and_compositions = [
        ("A wide panoramic mountain landscape", "landscape"),
        ("A tall skyscraper reaching into clouds", "portrait"),
        ("A perfectly balanced zen garden", "square"),
        ("An expansive desert horizon", "wide"),
    ]

    images = []

    # Generate images
    for prompt, composition_type in prompts_and_compositions:
        logger.info(f"Generating {composition_type} composition: {prompt}")
        result = await a_generate_image__genai(
            prompt=prompt, model="gemini-2.5-flash-image-preview"
        )
        assert result.image is not None
        images.append((prompt, composition_type, result.image))

    # Create a 2x2 grid
    fig, axes = plt.subplots(2, 2, figsize=(14, 14))
    fig.suptitle("Different Composition Types (all 1:1 aspect ratio)", fontsize=16)

    for ax, (prompt, comp_type, img_data) in zip(axes.flat, images):
        img = img_data.to_pil_image()
        ax.imshow(img)
        ax.axis("off")
        ax.set_title(f"{comp_type.capitalize()}: {prompt[:30]}...", fontsize=10)

    plt.tight_layout()

    # Save to temp file
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        plt.savefig(tmp.name, dpi=150, bbox_inches="tight")
        logger.info(f"Saved visualization to: {tmp.name}")

    # Show the plot
    plt.show()

    logger.info(
        "Visual verification complete - check composition variety within square format"
    )


@pytest.mark.visual
@pytest.mark.integration
@pytest.mark.asyncio
@injected_pytest(design())
async def test_visual_generate_then_edit(a_edit_image__genai, logger, /):
    """Generate an image, then edit it, and display both for visual comparison."""
    logger.info("Starting visual test for generate-then-edit workflow")

    # Step 1: Generate an initial image using a_edit_image__genai without input
    initial_prompt = "A simple landscape with mountains and a clear blue sky"
    logger.info(
        f"Generating initial image using edit function without input: {initial_prompt}"
    )

    initial_result = await a_edit_image__genai(
        input_images=[],  # Empty list to generate from scratch
        prompt=initial_prompt,
        model="gemini-2.5-flash-image-preview",
    )

    assert initial_result.image is not None
    logger.info("Initial image generated successfully using edit function")

    # Convert generated image to PIL Image for editing
    initial_pil_image = initial_result.image.to_pil_image()

    # Step 2: Edit the generated image
    edit_prompt = (
        "Add a rainbow, birds flying in the sky, and make the mountains snow-capped"
    )
    logger.info(f"Editing image with prompt: {edit_prompt}")

    edited_result = await a_edit_image__genai(
        input_images=[initial_pil_image],
        prompt=edit_prompt,
        model="gemini-2.5-flash-image-preview",
    )

    assert edited_result.image is not None
    logger.info("Image edited successfully")

    # Step 3: Display both images side by side
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))

    # Display original generated image
    ax1.imshow(initial_pil_image)
    ax1.axis("off")
    ax1.set_title(
        f"Original Generated Image\nPrompt: {initial_prompt[:50]}...", fontsize=12
    )

    # Display edited image
    edited_pil_image = edited_result.image.to_pil_image()
    ax2.imshow(edited_pil_image)
    ax2.axis("off")
    ax2.set_title(f"Edited Image\nEdit: {edit_prompt[:50]}...", fontsize=12)

    plt.suptitle("Generate-Then-Edit Workflow Test", fontsize=16, fontweight="bold")
    plt.tight_layout()

    # Save visualization to temp file
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        plt.savefig(tmp.name, dpi=150, bbox_inches="tight")
        logger.info(f"Saved generate-then-edit visualization to: {tmp.name}")

    # Show the plot (will display if running interactively)
    plt.show()

    logger.info(
        "Generate-then-edit visual test complete - compare original and edited images"
    )

    # Optional: Also save individual images for closer inspection
    with tempfile.NamedTemporaryFile(suffix="_original.png", delete=False) as tmp_orig:
        initial_result.image.save(tmp_orig.name)
        logger.info(f"Saved original image to: {tmp_orig.name}")

    with tempfile.NamedTemporaryFile(suffix="_edited.png", delete=False) as tmp_edit:
        edited_result.image.save(tmp_edit.name)
        logger.info(f"Saved edited image to: {tmp_edit.name}")


__design__ = design(
    a_generate_image__genai=a_generate_image__genai,
    a_edit_image__genai=a_edit_image__genai,
    a_describe_image__genai=a_describe_image__genai,
)
