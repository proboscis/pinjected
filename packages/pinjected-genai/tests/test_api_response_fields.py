"""Test to inspect what fields Google Gen AI API returns, especially for token usage."""

import pytest
from pinjected import design
from pinjected.test import injected_pytest
from google.genai import types
from PIL import Image
import io
from loguru import logger
import json
from pinjected_genai.clients import genai_client


# Test design for dependency injection
def get_test_di():
    """Get test design for dependency injection."""
    return design(
        logger=logger,
        genai_client=genai_client,
    )


@injected_pytest(get_test_di())
@pytest.mark.asyncio
async def test_text_generation_response_fields(genai_client, logger, /):
    """Test what fields are returned by Gen AI API for text generation."""
    logger.info("Testing text generation response fields...")

    response = await genai_client.aio.models.generate_content(
        model="gemini-2.5-flash",
        contents="Hello, please say hi back",
    )

    logger.info(f"Response type: {type(response)}")
    logger.info(f"Response attributes: {dir(response)}")

    # Check for various possible token/usage fields
    token_fields = [
        "usage_metadata",
        "usage",
        "token_count",
        "tokens",
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
        "input_token_count",
        "output_token_count",
        "cached_content_token_count",
        "candidates_token_count",
    ]

    for field in token_fields:
        if hasattr(response, field):
            value = getattr(response, field)
            logger.info(f"Found field '{field}': {value}")
            if value is not None:
                logger.info(f"  Type: {type(value)}")
                if hasattr(value, "__dict__"):
                    logger.info(f"  Attributes: {value.__dict__}")

    # Check candidates
    if response.candidates:
        candidate = response.candidates[0]
        logger.info(f"Candidate type: {type(candidate)}")
        logger.info(f"Candidate attributes: {dir(candidate)}")

        for field in token_fields:
            if hasattr(candidate, field):
                value = getattr(candidate, field)
                logger.info(f"Candidate has field '{field}': {value}")

    # Try to find any field with 'token' in the name
    all_attrs = dir(response)
    token_related = [attr for attr in all_attrs if "token" in attr.lower()]
    logger.info(f"All token-related attributes: {token_related}")

    # Check if response can be serialized to see structure
    try:
        if hasattr(response, "__dict__"):
            logger.info("Response __dict__:")
            for key, value in response.__dict__.items():
                logger.info(f"  {key}: {type(value)}")
    except Exception as e:
        logger.info(f"Could not access __dict__: {e}")


@injected_pytest(get_test_di())
@pytest.mark.asyncio
async def test_image_generation_response_fields(genai_client, logger, /):
    """Test what fields are returned by Gen AI API for image generation."""
    logger.info("Testing image generation response fields...")

    config = types.GenerateContentConfig(
        temperature=0.9,
        max_output_tokens=8192,
        response_modalities=["TEXT", "IMAGE"],  # Enable image generation
    )

    response = await genai_client.aio.models.generate_content(
        model="gemini-2.5-flash-image-preview",
        contents="Generate an image of a red circle on white background",
        config=config,
    )

    logger.info(f"Image generation response type: {type(response)}")
    logger.info(f"Image generation response attributes: {dir(response)}")

    # Check for token/usage fields specific to image generation
    token_fields = [
        "usage_metadata",
        "usage",
        "token_count",
        "tokens",
        "image_tokens",
        "image_token_count",
        "generation_tokens",
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
    ]

    for field in token_fields:
        if hasattr(response, field):
            value = getattr(response, field)
            logger.info(f"Found field '{field}': {value}")
            if value is not None and hasattr(value, "__dict__"):
                logger.info(f"  Field details: {value.__dict__}")

    # Check if image was generated and what metadata it has
    if response.candidates:
        for candidate in response.candidates:
            if candidate.content and candidate.content.parts:
                for part in candidate.content.parts:
                    if part.inline_data:
                        logger.info("Found generated image!")
                        logger.info(f"Image part attributes: {dir(part)}")
                        if hasattr(part, "metadata"):
                            logger.info(f"Image metadata: {part.metadata}")
                        if hasattr(part.inline_data, "token_count"):
                            logger.info(
                                f"Image token count: {part.inline_data.token_count}"
                            )


@injected_pytest(get_test_di())
@pytest.mark.asyncio
async def test_image_input_response_fields(genai_client, logger, /):
    """Test what fields are returned when sending an image as input."""
    logger.info("Testing image input response fields...")

    # Create a simple test image
    img = Image.new("RGB", (100, 100), color="red")
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format="PNG")
    image_bytes = img_byte_arr.getvalue()

    # Send image with prompt
    contents = [
        "Describe this image",
        types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
    ]

    response = await genai_client.aio.models.generate_content(
        model="gemini-2.5-flash", contents=contents
    )

    logger.info(f"Image input response type: {type(response)}")

    # Specifically look for token counts when image is input
    token_fields = [
        "usage_metadata",
        "usage",
        "token_count",
        "input_token_count",
        "prompt_token_count",
        "image_input_tokens",
        "multimodal_tokens",
    ]

    for field in token_fields:
        if hasattr(response, field):
            value = getattr(response, field)
            if value is not None:
                logger.info(f"Found field '{field}': {value}")
                if hasattr(value, "__dict__"):
                    logger.info(f"  Details: {value.__dict__}")

    # Check _raw attribute which might contain API response
    if hasattr(response, "_raw"):
        logger.info("Found _raw attribute!")
        raw = response._raw
        logger.info(f"_raw type: {type(raw)}")
        if hasattr(raw, "usage_metadata"):
            logger.info(f"_raw.usage_metadata: {raw.usage_metadata}")

    # Check if there's a to_dict method
    if hasattr(response, "to_dict"):
        try:
            response_dict = response.to_dict()
            logger.info("Response as dict:")
            logger.info(json.dumps(response_dict, indent=2, default=str))
        except Exception as e:
            logger.info(f"Could not convert to dict: {e}")


@injected_pytest(get_test_di())
@pytest.mark.asyncio
async def test_response_proto_fields(genai_client, logger, /):
    """Test to check if response has protobuf fields with usage info."""
    logger.info("Testing for protobuf fields in response...")

    response = await genai_client.aio.models.generate_content(
        model="gemini-2.5-flash",
        contents="Count to 5",
    )

    # Check for protobuf-style fields
    proto_fields = ["_pb", "_proto", "pb", "proto"]
    for field in proto_fields:
        if hasattr(response, field):
            logger.info(f"Found proto field '{field}'")
            proto_obj = getattr(response, field)
            logger.info(f"  Type: {type(proto_obj)}")
            if hasattr(proto_obj, "usage_metadata"):
                logger.info(f"  usage_metadata: {proto_obj.usage_metadata}")

    # Try to access as message descriptor
    if hasattr(response, "DESCRIPTOR"):
        logger.info("Found DESCRIPTOR (protobuf)")
        descriptor = response.DESCRIPTOR
        logger.info(f"Fields: {[f.name for f in descriptor.fields]}")

    # Check model metadata
    if hasattr(response, "model_metadata"):
        logger.info(f"model_metadata: {response.model_metadata}")

    # Check for response metadata
    if hasattr(response, "metadata"):
        logger.info(f"metadata: {response.metadata}")
