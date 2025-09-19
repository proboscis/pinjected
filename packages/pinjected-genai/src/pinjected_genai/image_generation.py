import base64
from dataclasses import dataclass
from io import BytesIO
from typing import Dict, List, Optional, Protocol, Tuple

from google import genai
from google.genai import types
from google.genai.types import MediaModality, GenerateContentResponseUsageMetadata
from loguru import logger
from PIL import Image
from pinjected import injected

from .genai_pricing import GenAIModelTable, GenAIState, log_generation_cost


TARGET_EDIT_IMAGE_DIMENSION = 1024


@dataclass
class SquarePadTransform:
    """Encapsulates how an image was resized and padded to fit a square canvas."""

    original_size: Tuple[int, int]
    scaled_size: Tuple[int, int]
    offset: Tuple[int, int]
    processing_mode: str
    image_format: str
    target_dim: int = TARGET_EDIT_IMAGE_DIMENSION

    @classmethod
    def prepare(
        cls,
        image: Image.Image,
        *,
        target_dim: int,
        logger,
        image_index: Optional[int] = None,
    ) -> Tuple[Image.Image, "SquarePadTransform"]:
        """Return a padded image plus the transform metadata used to produce it."""

        original_width, original_height = image.size
        scale_ratio = target_dim / max(original_width, original_height)
        scaled_width = max(1, round(original_width * scale_ratio))
        scaled_height = max(1, round(original_height * scale_ratio))
        offset_x = max(0, (target_dim - scaled_width) // 2)
        offset_y = max(0, (target_dim - scaled_height) // 2)

        processing_mode, pad_color = cls._processing_mode_and_pad_color(image)
        working_image = image.convert(processing_mode)
        resized_image = working_image.resize(
            (scaled_width, scaled_height), Image.LANCZOS
        )
        padded_image = Image.new(processing_mode, (target_dim, target_dim), pad_color)
        padded_image.paste(resized_image, (offset_x, offset_y))

        if (scaled_width, scaled_height) != (target_dim, target_dim):
            image_number = image_index + 1 if image_index is not None else "?"
            logger.warning(
                "Scaled and padded input image %s from %sx%s to %sx%s with offsets (%s, %s)",
                image_number,
                original_width,
                original_height,
                scaled_width,
                scaled_height,
                offset_x,
                offset_y,
            )

        transform = cls(
            original_size=(original_width, original_height),
            scaled_size=(scaled_width, scaled_height),
            offset=(offset_x, offset_y),
            processing_mode=processing_mode,
            image_format=(image.format or "PNG").upper(),
            target_dim=target_dim,
        )
        return padded_image, transform

    @staticmethod
    def _processing_mode_and_pad_color(image: Image.Image) -> Tuple[str, object]:
        if image.mode in {"RGBA", "LA"} or (
            image.mode == "P" and "transparency" in image.info
        ):
            return "RGBA", (0, 0, 0, 0)
        if image.mode == "L":
            return "L", 0
        return "RGB", (0, 0, 0)

    @property
    def mime_type(self) -> str:
        return f"image/{self.image_format.lower()}"

    def to_bytes(self, padded_image: Image.Image) -> bytes:
        save_image = padded_image
        if self.image_format in {"JPEG", "JPG"} and save_image.mode == "RGBA":
            save_image = save_image.convert("RGB")
        buffer = BytesIO()
        save_image.save(buffer, format=self.image_format)
        return buffer.getvalue()

    @staticmethod
    def _format_from_mime_type(mime_type: Optional[str]) -> Optional[str]:
        if mime_type and "/" in mime_type:
            return mime_type.split("/")[-1].upper()
        return None

    def restore(self, image_bytes: bytes, mime_type: Optional[str], logger) -> bytes:
        """Crop and resize the generated image back to the original dimensions."""

        try:
            with Image.open(BytesIO(image_bytes)) as edited_image:
                width, height = edited_image.size
                if width == 0 or height == 0:
                    logger.warning(
                        "Generated image had invalid dimensions: %sx%s", width, height
                    )
                    return image_bytes

                offset_x, offset_y = self.offset
                scaled_width, scaled_height = self.scaled_size

                left = min(max(offset_x, 0), width)
                top = min(max(offset_y, 0), height)
                right = min(width, left + scaled_width)
                bottom = min(height, top + scaled_height)

                if right <= left or bottom <= top:
                    logger.warning(
                        "Skipping post-processing; computed crop box (%s, %s, %s, %s) is invalid for size %sx%s",
                        left,
                        top,
                        right,
                        bottom,
                        width,
                        height,
                    )
                    return image_bytes

                cropped = edited_image.crop((left, top, right, bottom))
                resized = cropped.resize(self.original_size, Image.LANCZOS)

                target_format = (
                    self._format_from_mime_type(mime_type) or self.image_format
                )
                output_image = resized
                if target_format in {"JPEG", "JPG"} and output_image.mode in {
                    "RGBA",
                    "LA",
                }:
                    output_image = output_image.convert("RGB")

                buffer = BytesIO()
                output_image.save(buffer, format=target_format)
                return buffer.getvalue()

        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning("Failed to post-process generated image: %s", exc)

        return image_bytes


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
        temperature: float = 0.9,
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
    temperature: float = 0.9,
) -> GenerationResult:
    """Edit/generate an image based on input images (can be empty or multiple) using Google Gen AI SDK."""

    logger.info(f"Editing {len(input_images)} image(s) with prompt: {prompt[:100]}...")

    try:
        # Build contents list with prompt and any input images
        contents = [prompt]
        first_transform: Optional[SquarePadTransform] = None

        # Add each input image to the contents
        for idx, img in enumerate(input_images):
            logger.info(f"Processing input image {idx + 1}")

            original_width, original_height = img.size

            if original_width == 0 or original_height == 0:
                logger.warning(
                    "Skipping input image %s due to zero dimension: %sx%s",
                    idx + 1,
                    original_width,
                    original_height,
                )
                continue

            padded_image, transform = SquarePadTransform.prepare(
                img,
                target_dim=TARGET_EDIT_IMAGE_DIMENSION,
                logger=logger,
                image_index=idx,
            )
            if first_transform is None:
                first_transform = transform

            image_bytes = transform.to_bytes(padded_image)

            contents.append(
                types.Part.from_bytes(
                    data=image_bytes,
                    mime_type=transform.mime_type,
                )
            )

        # Configure generation with image output
        config = types.GenerateContentConfig(
            temperature=temperature,
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
                                processed_bytes = image_bytes
                                if first_transform:
                                    processed_bytes = first_transform.restore(
                                        image_bytes=image_bytes,
                                        mime_type=mime_type,
                                        logger=logger,
                                    )
                                generated_image = GeneratedImage(
                                    image_data=processed_bytes,
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
