import base64
from dataclasses import dataclass
from io import BytesIO
from typing import List, Optional, Protocol

from google import genai
from google.genai import types
from loguru import logger
from PIL import Image

from pinjected import injected


@dataclass
class GeneratedImage:
    image_data: bytes
    mime_type: str
    prompt_used: str

    def to_pil_image(self) -> Image.Image:
        return Image.open(BytesIO(self.image_data))

    def save(self, path: str) -> None:
        with open(path, "wb") as f:
            f.write(self.image_data)

    def to_base64(self) -> str:
        return base64.b64encode(self.image_data).decode("utf-8")


@dataclass
class GenerationResult:
    text: Optional[str]
    image: GeneratedImage
    model_used: str


class AGenerateImageProtocol(Protocol):
    async def __call__(
        self,
        prompt: str,
        model: str,
    ) -> GenerationResult: ...


@injected(protocol=AGenerateImageProtocol)
async def a_generate_image__genai(
    genai_client: genai.Client,
    logger: logger,
    /,
    prompt: str,
    model: str,
) -> GenerationResult:
    """Generate an image using Google Gen AI SDK with nano-banana model."""

    logger.info(f"Generating image with prompt: {prompt[:100]}...")

    try:
        # Configure generation with image output
        config = types.GenerateContentConfig(
            temperature=0.9,
            max_output_tokens=8192,
            response_modalities=["TEXT", "IMAGE"],  # Enable image generation
        )

        # Generate content with the model
        response = await genai_client.aio.models.generate_content(
            model=model, contents=prompt, config=config
        )

        # Process response to extract image and text
        generated_image = None
        text_parts = []

        if response.candidates:
            for candidate in response.candidates:
                if candidate.content and candidate.content.parts:
                    for part in candidate.content.parts:
                        # Extract text if present
                        if part.text:
                            text_parts.append(part.text)
                        # Extract image if present
                        elif part.inline_data and part.inline_data.data:
                            # The image is in inline_data
                            image_bytes = part.inline_data.data
                            mime_type = part.inline_data.mime_type
                            if image_bytes and not generated_image:  # Take first image
                                generated_image = GeneratedImage(
                                    image_data=image_bytes,
                                    mime_type=mime_type or "image/png",
                                    prompt_used=prompt,
                                )

        combined_text = "\n".join(text_parts) if text_parts else None

        if not generated_image:
            error_msg = (
                f"Model {model} did not return any image for prompt: {prompt[:100]}"
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

        logger.info("Successfully generated image")

        return GenerationResult(
            text=combined_text, image=generated_image, model_used=model
        )

    except Exception as e:
        logger.error(f"Failed to generate image: {e}")
        raise


class AEditImageProtocol(Protocol):
    async def __call__(
        self,
        input_images: List[Image.Image],
        prompt: str,
        model: str,
    ) -> GenerationResult: ...


@injected(protocol=AEditImageProtocol)
async def a_edit_image__genai(
    genai_client: genai.Client,
    logger: logger,
    /,
    input_images: List[Image.Image],
    prompt: str,
    model: str,
) -> GenerationResult:
    """Edit/generate an image based on input images (can be empty or multiple) using Google Gen AI SDK."""

    logger.info(f"Editing {len(input_images)} image(s) with prompt: {prompt[:100]}...")

    try:
        # Build contents list with prompt and any input images
        contents = [prompt]

        # Add each input image to the contents
        for idx, img in enumerate(input_images):
            logger.info(f"Processing input image {idx + 1}")

            # Convert PIL Image to bytes
            img_byte_arr = BytesIO()
            img.save(img_byte_arr, format=img.format if img.format else "PNG")
            image_bytes = img_byte_arr.getvalue()

            contents.append(
                types.Part.from_bytes(
                    data=image_bytes,
                    mime_type=f"image/{img.format.lower()}"
                    if img.format
                    else "image/png",
                )
            )

        # Configure generation with image output
        config = types.GenerateContentConfig(
            temperature=0.9,
            max_output_tokens=8192,
            response_modalities=["TEXT", "IMAGE"],  # Enable image generation
        )

        # Generate content with the model
        response = await genai_client.aio.models.generate_content(
            model=model, contents=contents, config=config
        )

        # Process response to extract image and text
        generated_image = None
        text_parts = []

        if response.candidates:
            for candidate in response.candidates:
                if candidate.content and candidate.content.parts:
                    for part in candidate.content.parts:
                        # Extract text if present
                        if part.text:
                            text_parts.append(part.text)
                        # Extract image if present
                        elif part.inline_data and part.inline_data.data:
                            # The image is in inline_data
                            image_bytes = part.inline_data.data
                            mime_type = part.inline_data.mime_type
                            if image_bytes and not generated_image:  # Take first image
                                generated_image = GeneratedImage(
                                    image_data=image_bytes,
                                    mime_type=mime_type or "image/png",
                                    prompt_used=f"Edit: {prompt}",
                                )

        combined_text = "\n".join(text_parts) if text_parts else None

        if not generated_image:
            error_msg = f"Model {model} did not return any edited image for prompt: {prompt[:100]}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        logger.info("Successfully edited image")

        return GenerationResult(
            text=combined_text, image=generated_image, model_used=model
        )

    except Exception as e:
        logger.error(f"Failed to edit image: {e}")
        raise


class ADescribeImageProtocol(Protocol):
    async def __call__(
        self,
        image_path: str,
        prompt: Optional[str] = None,
        model: str = "gemini-2.5-flash",
    ) -> str: ...


@injected(protocol=ADescribeImageProtocol)
async def a_describe_image__genai(
    genai_client: genai.Client,
    logger: logger,
    /,
    image_path: str,
    prompt: Optional[str] = None,
    model: str = "gemini-2.5-flash",
) -> str:
    """Describe an image using Google Gen AI SDK."""
    logger.info(f"Describing image: {image_path}")

    try:
        # Load the image
        img = Image.open(image_path)

        # Convert PIL Image to bytes
        img_byte_arr = BytesIO()
        img.save(img_byte_arr, format=img.format if img.format else "PNG")
        image_bytes = img_byte_arr.getvalue()

        # Build the prompt with image
        text_prompt = prompt if prompt else "Describe this image in detail."

        # Create content with image
        contents = [
            text_prompt,
            types.Part.from_bytes(
                data=image_bytes,
                mime_type=f"image/{img.format.lower()}" if img.format else "image/png",
            ),
        ]

        # Configure generation
        config = types.GenerateContentConfig(
            temperature=0.7,
            max_output_tokens=2048,
        )

        # Generate description
        response = await genai_client.aio.models.generate_content(
            model=model, contents=contents, config=config
        )

        if response.text:
            logger.info("Successfully described image")
            return response.text
        else:
            logger.warning("No description generated for image")
            return ""

    except Exception as e:
        logger.error(f"Failed to describe image: {e}")
        raise
