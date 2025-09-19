import base64
from dataclasses import dataclass
from io import BytesIO
from typing import List, Optional, Protocol, Dict

from google import genai
from google.genai import types
from google.genai.types import MediaModality, GenerateContentResponseUsageMetadata
from loguru import logger
from PIL import Image

from pinjected import injected

from .genai_pricing import GenAIModelTable, GenAIState, log_generation_cost


def extract_modality_specific_tokens(
    usage_metadata: GenerateContentResponseUsageMetadata,
) -> Dict[str, int]:
    """Extract modality-specific token counts from usage metadata.

    Args:
        usage_metadata: The GenerateContentResponseUsageMetadata from Gen AI API

    Returns:
        Dict with keys: text_input_tokens, text_output_tokens, image_input_tokens, image_output_tokens
    """
    result = {
        "text_input_tokens": 0,
        "text_output_tokens": 0,
        "image_input_tokens": 0,
        "image_output_tokens": 0,
    }

    # Process input token details
    if usage_metadata.prompt_tokens_details:
        for detail in usage_metadata.prompt_tokens_details:
            if detail.modality == MediaModality.TEXT:
                result["text_input_tokens"] += detail.token_count
            elif detail.modality == MediaModality.IMAGE:
                result["image_input_tokens"] += detail.token_count

    # Process output token details
    if usage_metadata.candidates_tokens_details:
        for detail in usage_metadata.candidates_tokens_details:
            if detail.modality == MediaModality.TEXT:
                result["text_output_tokens"] += detail.token_count
            elif detail.modality == MediaModality.IMAGE:
                result["image_output_tokens"] += detail.token_count

    return result


def extract_token_counts_from_usage_metadata(usage_metadata) -> Dict[str, int]:
    """Extract modality-specific token counts from usage_metadata.

    Returns a dict with keys:
    - text_input_tokens
    - text_output_tokens
    - image_input_tokens
    - image_output_tokens

    Raises:
        ValueError: If usage_metadata is None or invalid format
    """
    if usage_metadata is None:
        raise ValueError(
            "usage_metadata is None - API did not return token usage information"
        )

    # If it's already the right type, use it directly
    assert isinstance(usage_metadata, GenerateContentResponseUsageMetadata)
    return extract_modality_specific_tokens(usage_metadata)


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
    genai_model_table: GenAIModelTable,
    genai_state: GenAIState,  # noqa: PINJ056
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

        # Calculate and log costs
        # Extract actual token counts from API response
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            # Use helper to extract modality-specific token counts
            usage = extract_token_counts_from_usage_metadata(response.usage_metadata)
            logger.debug(
                f"Using actual token counts from API: text_in={usage['text_input_tokens']}, text_out={usage['text_output_tokens']}, image_in={usage['image_input_tokens']}, image_out={usage['image_output_tokens']}"
            )
        else:
            error_msg = (
                "API did not provide usage_metadata - cannot determine token counts"
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Log the cost (state update happens within the DI framework)
        log_generation_cost(
            usage=usage,
            model=model,
            genai_model_table=genai_model_table,
            genai_state=genai_state,
            logger=logger,
        )

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
    genai_model_table: GenAIModelTable,
    genai_state: GenAIState,  # noqa: PINJ056
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

            image_format = (img.format or "PNG").upper()
            processed_img = img
            original_width, original_height = img.size
            max_dimension = max(original_width, original_height)

            if max_dimension > 1024:
                scale_ratio = 1024 / max_dimension
                new_width = max(1, int(original_width * scale_ratio))
                new_height = max(1, int(original_height * scale_ratio))
                processed_img = img.resize((new_width, new_height), Image.LANCZOS)
                logger.warning(
                    "Scaled input image %s from %sx%s to %sx%s to satisfy 1024px max dimension",
                    idx + 1,
                    original_width,
                    original_height,
                    new_width,
                    new_height,
                )

            # Convert PIL Image to bytes after optional scaling
            img_byte_arr = BytesIO()
            processed_img.save(img_byte_arr, format=image_format)
            image_bytes = img_byte_arr.getvalue()

            contents.append(
                types.Part.from_bytes(
                    data=image_bytes,
                    mime_type=f"image/{image_format.lower()}",
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

        # Calculate and log costs
        # Extract actual token counts from API response
        # Use helper to extract modality-specific token counts
        usage = extract_token_counts_from_usage_metadata(response.usage_metadata)
        logger.debug(
            f"Using actual token counts from API: text_in={usage['text_input_tokens']}, text_out={usage['text_output_tokens']}, image_in={usage['image_input_tokens']}, image_out={usage['image_output_tokens']}"
        )

        # Log the cost (state update happens within the DI framework)
        log_generation_cost(
            usage=usage,
            model=model,
            genai_model_table=genai_model_table,
            genai_state=genai_state,
            logger=logger,
        )

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
    genai_model_table: GenAIModelTable,
    genai_state: GenAIState,  # noqa: PINJ056
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

            # Calculate and log costs
            text_prompt = prompt if prompt else "Describe this image in detail."
            # Extract actual token counts from API response
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                logger.debug(
                    f"Raw usage_metadata type: {type(response.usage_metadata)}"
                )
                logger.debug(f"Raw usage_metadata: {response.usage_metadata}")
                # Use helper to extract modality-specific token counts
                usage = extract_token_counts_from_usage_metadata(
                    response.usage_metadata
                )
                logger.debug(
                    f"Using actual token counts from API: text_in={usage['text_input_tokens']}, text_out={usage['text_output_tokens']}, image_in={usage['image_input_tokens']}, image_out={usage['image_output_tokens']}"
                )
            else:
                error_msg = (
                    "API did not provide usage_metadata - cannot determine token counts"
                )
                logger.error(error_msg)
                raise ValueError(error_msg)

            # Log the cost (returns updated state but doesn't mutate)
            log_generation_cost(
                usage=usage,
                model=model,
                genai_model_table=genai_model_table,
                genai_state=genai_state,
                logger=logger,
            )

            return response.text
        else:
            error_msg = f"No description generated for image: {image_path}"
            logger.error(error_msg)
            raise ValueError(error_msg)

    except Exception as e:
        logger.error(f"Failed to describe image: {e}")
        raise
