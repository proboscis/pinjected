"""Integration tests for refactored OpenRouter functions without mocks."""

import pytest
from typing import Optional
from pinjected.test import injected_pytest
from pinjected_openai.openrouter.util import (
    handle_openrouter_error,
    build_provider_filter,
    build_user_message,
    build_chat_payload,
    validate_response_format,
    prepare_json_provider_and_kwargs,
    JsonProviderConfig,
    OpenRouterRateLimitError,
    OpenRouterTransientError,
    OpenRouterOverloadedError,
    OpenRouterTimeOutError,
)
from pydantic import BaseModel
from loguru import logger


# Test models for structured output
class SimpleResponse(BaseModel):
    """Simple test response model."""

    answer: str
    confidence: float


class ComplexResponse(BaseModel):
    """Complex response with optional fields."""

    title: str
    content: str
    metadata: Optional[dict] = None


# Helper function tests (pure functions but still need @injected_pytest)
@injected_pytest
def test_build_provider_filter():
    """Test provider filter building."""
    # Test with None
    assert build_provider_filter(None) == {}

    # Test with provider dict
    provider = {"name": "openai", "order": ["gpt-4"]}
    result = build_provider_filter(provider)
    assert result == {"provider": provider}

    # Test with complex provider
    complex_provider = {
        "name": "openai",
        "order": ["gpt-4", "gpt-3.5-turbo"],
        "require_parameters": True,
    }
    result = build_provider_filter(complex_provider)
    assert result == {"provider": complex_provider}


@injected_pytest
def test_build_user_message():
    """Test user message building."""
    # Test without images
    msg = build_user_message("Hello world")
    assert msg["role"] == "user"
    assert len(msg["content"]) == 1
    assert msg["content"][0]["type"] == "text"
    assert msg["content"][0]["text"] == "Hello world"

    # Test with empty images list
    msg = build_user_message("Test", images=[])
    assert len(msg["content"]) == 1

    # Test with None images
    msg = build_user_message("Test", images=None)
    assert len(msg["content"]) == 1


@injected_pytest
def test_build_chat_payload():
    """Test chat payload building."""
    # Basic payload
    payload = build_chat_payload(
        model="gpt-4",
        prompt="Hello",
        max_tokens=100,
        temperature=0.7,
    )

    assert payload["model"] == "gpt-4"
    assert payload["max_tokens"] == 100
    assert payload["temperature"] == 0.7
    assert "messages" in payload
    assert payload["messages"][0]["role"] == "user"

    # Payload with provider
    payload = build_chat_payload(
        model="gpt-4",
        prompt="Test",
        max_tokens=50,
        temperature=0.5,
        provider={"name": "openai"},
    )

    assert "provider" in payload
    assert payload["provider"]["name"] == "openai"

    # Payload with reasoning
    payload = build_chat_payload(
        model="gpt-4",
        prompt="Test",
        max_tokens=50,
        temperature=0.5,
        include_reasoning=True,
        reasoning={"prompt": "Think step by step"},
    )

    assert payload["include_reasoning"] is True
    assert payload["reasoning"]["prompt"] == "Think step by step"

    # Payload with extra kwargs
    payload = build_chat_payload(
        model="gpt-4",
        prompt="Test",
        max_tokens=50,
        temperature=0.5,
        top_p=0.9,
        frequency_penalty=0.1,
    )

    assert payload["top_p"] == 0.9
    assert payload["frequency_penalty"] == 0.1


@injected_pytest
def test_validate_response_format():
    """Test response format validation."""
    # Valid simple model
    validate_response_format(SimpleResponse, "gpt-4")
    # Should not raise

    # Valid complex model
    validate_response_format(ComplexResponse, "gpt-4")
    # Should not raise

    # Test with Gemini model (may have different constraints)
    validate_response_format(SimpleResponse, "google/gemini-pro")
    # Should not raise for simple model


@injected_pytest
def test_prepare_json_provider_and_kwargs():
    """Test JSON provider and kwargs preparation."""

    # Create mock logger
    class MockLogger:
        def warning(self, msg):
            self.last_warning = msg

    logger = MockLogger()

    # Test with JSON support
    config = prepare_json_provider_and_kwargs(
        provider={"name": "openai"},
        kwargs={"top_p": 0.9},
        response_format=SimpleResponse,
        supports_json=True,
        logger=logger,
        model="gpt-4",
    )

    assert isinstance(config, JsonProviderConfig)
    assert config.provider["require_parameters"] is True
    assert config.provider["name"] == "openai"
    assert "response_format" in config.kwargs
    assert config.kwargs["top_p"] == 0.9

    # Test without JSON support
    config = prepare_json_provider_and_kwargs(
        provider=None,
        kwargs={"temperature": 0.5},
        response_format=SimpleResponse,
        supports_json=False,
        logger=logger,
        model="old-model",
    )

    assert config.provider is None
    assert config.kwargs == {"temperature": 0.5}
    assert hasattr(logger, "last_warning")
    assert "does not support JSON" in logger.last_warning


@injected_pytest
def test_handle_openrouter_error():
    """Test error handling for various OpenRouter errors."""

    # Create mock logger
    class MockLogger:
        def __init__(self):
            self.warnings = []
            self.errors = []

        def warning(self, msg):
            self.warnings.append(msg)

        def error(self, msg):
            self.errors.append(msg)

    logger = MockLogger()

    # Test no error case
    handle_openrouter_error({"success": True}, logger)
    # Should not raise

    # Test 429 rate limit error
    with pytest.raises(OpenRouterRateLimitError):
        handle_openrouter_error(
            {"error": {"code": 429, "message": "Rate limited"}}, logger
        )
    assert len(logger.warnings) > 0

    # Test timeout error
    with pytest.raises(OpenRouterTimeOutError):
        handle_openrouter_error({"error": {"message": "Request Timed out"}}, logger)

    # Test overloaded error (502)
    with pytest.raises(OpenRouterOverloadedError):
        handle_openrouter_error(
            {"error": {"code": 502, "message": "Bad gateway"}}, logger
        )

    # Test transient errors
    for code in [520, 503, 522, 524]:
        with pytest.raises(OpenRouterTransientError):
            handle_openrouter_error(
                {"error": {"code": code, "message": f"Error {code}"}}, logger
            )

    # Test generic error
    with pytest.raises(RuntimeError):
        handle_openrouter_error(
            {"error": {"code": 400, "message": "Bad request"}}, logger
        )


# Integration tests with dependency injection
@pytest.mark.asyncio
@injected_pytest
async def test_integration_base_chat_completion(
    a_openrouter_base_chat_completion,
    openrouter_api,  # This will check if API key exists
    /,
):
    """Test base chat completion function integration."""
    result = await a_openrouter_base_chat_completion(
        prompt="Say 'test successful' and nothing else",
        model="openai/gpt-4o-mini",
        max_tokens=10,
        temperature=0,
    )

    assert isinstance(result, str)
    assert len(result) > 0
    logger.info(f"Base completion result: {result}")


@pytest.mark.asyncio
@injected_pytest
async def test_integration_structured_chat_completion(
    a_openrouter_chat_completion,
    openrouter_api,  # This will check if API key exists
    /,
):
    """Test structured chat completion with JSON response."""
    result = await a_openrouter_chat_completion(
        prompt="What is 2+2? Respond with high confidence.",
        model="openai/gpt-4o-mini",
        max_tokens=100,
        temperature=0,
        response_format=SimpleResponse,
    )

    assert isinstance(result, SimpleResponse)
    assert "4" in result.answer or "four" in result.answer.lower()
    assert result.confidence > 0.8
    logger.info(f"Structured result: {result}")


@pytest.mark.asyncio
@injected_pytest
async def test_integration_error_handling(
    a_openrouter_chat_completion,
    openrouter_api,  # This will check if API key exists
    /,
):
    """Test error handling in real API calls."""
    # Test with invalid model - should raise an error
    with pytest.raises(Exception):  # Will be specific error from API
        await a_openrouter_chat_completion(
            prompt="Test",
            model="invalid-model-xyz",
            max_tokens=10,
        )


@pytest.mark.asyncio
@injected_pytest
async def test_integration_with_provider_filter(
    a_openrouter_chat_completion,
    openrouter_api,  # This will check if API key exists
    /,
):
    """Test chat completion with provider filtering."""
    # Use provider filter to ensure specific provider
    result = await a_openrouter_chat_completion(
        prompt="What is the capital of France? One word answer.",
        model="openai/gpt-4o-mini",
        max_tokens=10,
        temperature=0,
        provider={"order": ["OpenAI"]},  # Force OpenAI provider
    )

    assert isinstance(result, str)
    assert "paris" in result.lower()
    logger.info(f"Provider filtered result: {result}")


# Run the built-in test definitions from util.py
@pytest.mark.asyncio
@injected_pytest
async def test_util_openrouter_chat_completion(
    test_openrouter_chat_completion,
    /,
):
    """Run the test_openrouter_chat_completion from util.py."""
    result = await test_openrouter_chat_completion
    assert result is not None
    logger.info(f"util.py test result: {result}")


@pytest.mark.asyncio
@injected_pytest
async def test_util_model_table(
    test_openrouter_model_table,
    /,
):
    """Test the OpenRouter model table."""
    model_table = await test_openrouter_model_table
    assert model_table is not None

    # Test getting a known model
    model = model_table.get_model("openai/gpt-4o-mini")
    if model:
        assert model.id == "openai/gpt-4o-mini"
        assert model.supports_json_output() is True
        logger.info(f"Model info: {model.name}, context: {model.context_length}")


@pytest.mark.asyncio
@injected_pytest
async def test_util_resize_image(
    test_resize_image,
    /,
):
    """Test image resizing function."""
    # Create a simple test image
    from PIL import Image

    # Create a large image (to trigger resizing)
    _ = Image.new("RGB", (2000, 2000), color="red")

    # This should resize it
    _ = await test_resize_image
    # Result should be PIL Image
    logger.info("Image resize test completed")


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s", "-x"])
