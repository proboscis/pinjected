"""Direct test for nano-banana (Gemini 2.5 Flash Image) model."""

import asyncio
import sys
import tempfile
from io import BytesIO

from google import genai
from google.auth import default
from google.genai import types
from PIL import Image


async def test_nano_banana_direct():
    """Test nano-banana directly without dependency injection."""
    # Get credentials
    credentials, project = default()
    print(f"Using project: {project}")

    # Create Gen AI client with Vertex AI mode and global endpoint - REQUIRED for nano-banana
    client = genai.Client(
        vertexai=True,
        project=project,
        location="global",  # REQUIRED for nano-banana
        credentials=credentials,
    )
    print("Created Gen AI client with global location")

    # Use the nano-banana model
    model_name = "gemini-2.5-flash-image-preview"
    print(f"Using model: {model_name}")

    # Configure for image generation
    generation_config = types.GenerateContentConfig(
        temperature=0.9,
        max_output_tokens=8192,
        response_modalities=["TEXT", "IMAGE"],  # Enable image output
    )

    # Generate an image
    prompt = "A simple red circle on white background, minimalist geometric art"
    print(f"\nGenerating image with prompt: {prompt}")

    response = await client.aio.models.generate_content(
        model=model_name, contents=prompt, config=generation_config
    )

    # Extract the image
    image_found = False
    if response.candidates:
        for candidate in response.candidates:
            if candidate.content and candidate.content.parts:
                for part in candidate.content.parts:
                    if hasattr(part, "text") and part.text:
                        print(f"Text response: {part.text[:200]}...")
                    elif hasattr(part, "inline_data") and part.inline_data:
                        print(f"Got image! MIME type: {part.inline_data.mime_type}")
                        print(f"Image data size: {len(part.inline_data.data)} bytes")

                        # Save the image
                        img = Image.open(BytesIO(part.inline_data.data))
                        with tempfile.NamedTemporaryFile(
                            suffix=".png", delete=False
                        ) as tmp:
                            img.save(tmp.name)
                            print(f"Saved image to: {tmp.name}")
                            print(f"Image size: {img.size}")

                        image_found = True

    if image_found:
        print("\n✅ Nano-banana (Gemini 2.5 Flash Image) test PASSED!")
    else:
        print("\n❌ No image generated - test FAILED")

    return image_found


if __name__ == "__main__":
    success = asyncio.run(test_nano_banana_direct())
    sys.exit(0 if success else 1)
