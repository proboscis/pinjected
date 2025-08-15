"""Tests for the refactored OpenRouter implementation."""

import httpx  # Import at top for proper module level import
import pytest
from unittest.mock import AsyncMock, MagicMock
from pinjected import design
from pinjected.test import injected_pytest
from pinjected_openai.openrouter.refactored_simple import (
    OpenRouterError,
    OpenRouterRateLimitError,
    OpenRouterTimeOutError,
    OpenRouterOverloadedError,
)
from pydantic import BaseModel
import PIL.Image


# Test models
class SampleResponse(BaseModel):
    message: str
    status: str


# ============================================================================
# API Call Tests
# ============================================================================


@pytest.mark.asyncio
@injected_pytest
async def test_a_openrouter_api_call_success(
    a_openrouter_api_call,
    /,
):
    """Test successful API call."""
    payload = {
        "model": "gpt-4",
        "messages": [{"role": "user", "content": "Hello"}],
        "max_tokens": 100,
    }

    result = await a_openrouter_api_call(payload)

    assert result is not None
    assert "choices" in result
    assert result["choices"][0]["message"]["content"] == "Mock response"


# ============================================================================
# Error Handling Tests
# ============================================================================


@injected_pytest
def test_handle_openrouter_error_no_error(
    handle_openrouter_error,
    /,
):
    """Test error handler with no error in response."""
    response = {
        "choices": [{"message": {"content": "Success"}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5},
    }

    # Should not raise
    handle_openrouter_error(response)


@injected_pytest
def test_handle_openrouter_error_rate_limit(
    handle_openrouter_error,
    /,
):
    """Test error handler with rate limit error."""
    response = {"error": {"code": 429, "message": "Rate limit exceeded"}}

    with pytest.raises(OpenRouterRateLimitError):
        handle_openrouter_error(response)


@injected_pytest
def test_handle_openrouter_error_timeout(
    handle_openrouter_error,
    /,
):
    """Test error handler with timeout error."""
    response = {"error": {"message": "Request Timed out"}}

    with pytest.raises(OpenRouterTimeOutError):
        handle_openrouter_error(response)


@injected_pytest
def test_handle_openrouter_error_overloaded(
    handle_openrouter_error,
    /,
):
    """Test error handler with overloaded error."""
    response = {"error": {"code": 502, "message": "Service Overloaded"}}

    with pytest.raises(OpenRouterOverloadedError):
        handle_openrouter_error(response)


@injected_pytest
def test_handle_openrouter_error_generic(
    handle_openrouter_error,
    /,
):
    """Test error handler with generic error."""
    response = {"error": {"message": "Something went wrong"}}

    with pytest.raises(OpenRouterError):
        handle_openrouter_error(response)


# ============================================================================
# Image Processing Tests
# ============================================================================


@pytest.mark.asyncio
@injected_pytest
async def test_a_process_image_for_api(
    a_process_image_for_api,
    /,
):
    """Test image processing for API submission."""
    # Create a small test image
    image = PIL.Image.new("RGB", (100, 100), color="red")

    result = await a_process_image_for_api(image)

    assert isinstance(result, str)
    # Base64 encoded string should not contain spaces or newlines
    assert " " not in result
    assert "\n" not in result


@pytest.mark.asyncio
@injected_pytest
async def test_a_process_image_for_api_rgba(
    a_process_image_for_api,
    /,
):
    """Test processing RGBA image."""
    # Create RGBA image
    image = PIL.Image.new("RGBA", (100, 100), color=(255, 0, 0, 128))

    result = await a_process_image_for_api(image)

    assert isinstance(result, str)
    # Should convert to RGB and encode


# ============================================================================
# Message Content Building Tests
# ============================================================================


@pytest.mark.asyncio
@injected_pytest
async def test_a_build_message_content_text_only(
    a_build_message_content,
    /,
):
    """Test building message content with text only."""
    content = await a_build_message_content("Hello world")

    assert len(content) == 1
    assert content[0]["type"] == "text"
    assert content[0]["text"] == "Hello world"


@pytest.mark.asyncio
@injected_pytest
async def test_a_build_message_content_with_images(
    a_build_message_content,
    /,
):
    """Test building message content with images."""
    image = PIL.Image.new("RGB", (100, 100), color="blue")
    content = await a_build_message_content("Describe this", images=[image])

    assert len(content) == 2
    assert content[0]["type"] == "text"
    assert content[0]["text"] == "Describe this"
    assert content[1]["type"] == "image_url"
    assert "data:image/jpeg;base64," in content[1]["image_url"]["url"]


# ============================================================================
# Response Format Tests
# ============================================================================


@injected_pytest
def test_format_response_for_json_supported_model(
    format_response_for_json,
    /,
):
    """Test formatting response for JSON-supporting model."""
    result = format_response_for_json(response_format=SampleResponse, model="gpt-4")

    # Mock model table says gpt-4 supports JSON
    assert result is not None
    assert result["type"] == "json_schema"
    assert "json_schema" in result
    assert result["json_schema"]["name"] == "response"


@injected_pytest
def test_format_response_for_json_unsupported_model(
    format_response_for_json,
    /,
):
    """Test formatting response for non-JSON-supporting model."""
    # Update mock to return False for this test
    result = format_response_for_json(
        response_format=SampleResponse, model="unsupported-model"
    )

    assert result is None


# ============================================================================
# JSON Parsing Tests
# ============================================================================


@pytest.mark.asyncio
@injected_pytest
async def test_a_parse_json_response_valid(
    a_parse_json_response,
    /,
):
    """Test parsing valid JSON response."""
    content = '{"message": "Hello", "status": "ok"}'

    result = await a_parse_json_response(content, SampleResponse)

    assert isinstance(result, SampleResponse)
    assert result.message == "Hello"
    assert result.status == "ok"


@pytest.mark.asyncio
@injected_pytest
async def test_a_parse_json_response_with_markdown(
    a_parse_json_response,
    /,
):
    """Test parsing JSON from markdown code block."""
    content = """Here's the response:
```json
{"message": "Hello", "status": "ok"}
```
"""

    result = await a_parse_json_response(content, SampleResponse)

    assert isinstance(result, SampleResponse)
    assert result.message == "Hello"
    assert result.status == "ok"


@pytest.mark.asyncio
@injected_pytest
async def test_a_parse_json_response_invalid(
    a_parse_json_response,
    /,
):
    """Test parsing invalid JSON raises error."""
    content = "Not JSON at all"

    with pytest.raises(Exception):
        await a_parse_json_response(content, SampleResponse)


# ============================================================================
# Main Function Tests
# ============================================================================


@pytest.mark.asyncio
@injected_pytest
async def test_a_refactored_chat_completion_simple(
    a_refactored_chat_completion,
    /,
):
    """Test basic chat completion."""
    result = await a_refactored_chat_completion(
        prompt="Hello", model="gpt-4", max_tokens=100, temperature=0.5
    )

    assert "result" in result
    assert result["result"] == "Mock response"


@pytest.mark.asyncio
@injected_pytest
async def test_a_refactored_chat_completion_with_images(
    a_refactored_chat_completion,
    /,
):
    """Test chat completion with images."""
    image = PIL.Image.new("RGB", (100, 100), color="green")

    result = await a_refactored_chat_completion(
        prompt="What's in this image?", model="gpt-4-vision", images=[image]
    )

    assert "result" in result
    assert result["result"] == "Mock response"


@pytest.mark.asyncio
@injected_pytest
async def test_a_refactored_chat_completion_structured(
    a_refactored_chat_completion,
    /,
):
    """Test chat completion with structured output."""
    # Mock to return JSON string for structured output
    result = await a_refactored_chat_completion(
        prompt="Generate a response", model="gpt-4", response_format=SampleResponse
    )

    assert "result" in result
    # Mock should parse the JSON response
    assert isinstance(result["result"], SampleResponse)


# ============================================================================
# Convenience Function Tests
# ============================================================================


@pytest.mark.asyncio
@injected_pytest
async def test_a_simple_completion(
    a_simple_completion,
    /,
):
    """Test simple text completion."""
    result = await a_simple_completion(prompt="Hello world", model="gpt-4")

    assert isinstance(result, str)
    assert result == "Mock response"


@pytest.mark.asyncio
@injected_pytest
async def test_a_json_completion(
    a_json_completion,
    /,
):
    """Test JSON completion."""
    result = await a_json_completion(
        prompt="Generate data", response_model=SampleResponse, model="gpt-4"
    )

    assert isinstance(result, SampleResponse)


@pytest.mark.asyncio
@injected_pytest
async def test_a_vision_completion(
    a_vision_completion,
    /,
):
    """Test vision completion."""
    image = PIL.Image.new("RGB", (100, 100), color="yellow")

    result = await a_vision_completion(
        prompt="Describe this", images=[image], model="gpt-4-vision"
    )

    assert isinstance(result, str)
    assert result == "Mock response"


# ============================================================================
# Test Design
# ============================================================================


# Mock httpx client for API calls
class MockAsyncClient:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def post(self, url, headers, json, timeout):
        # Return mock response
        if "error_test" in json.get("model", ""):
            return MagicMock(json=lambda: {"error": {"message": "Test error"}})

        # Check if structured output is requested
        if "response_format" in json:
            # Return JSON response for structured output
            return MagicMock(
                json=lambda: {
                    "choices": [
                        {
                            "message": {
                                "content": '{"message": "Structured response", "status": "success"}'
                            }
                        }
                    ],
                    "usage": {"prompt_tokens": 10, "completion_tokens": 20},
                }
            )

        return MagicMock(
            json=lambda: {
                "choices": [{"message": {"content": "Mock response"}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            }
        )


# Monkey-patch httpx for testing
httpx.AsyncClient = MockAsyncClient


__design__ = design(
    # API configuration
    openrouter_api_key="test_key",
    openrouter_timeout_sec=30.0,
    # Logger mock
    logger=MagicMock(info=MagicMock(), warning=MagicMock()),
    # Model table mock
    model_table=MagicMock(
        supports_json_output=MagicMock(
            side_effect=lambda model: model in ["gpt-4", "gpt-4-vision", "gpt-4o"]
        )
    ),
    # Mock for image processing dependency in a_build_message_content
    a_process_image_for_api=AsyncMock(return_value="base64encodedimage"),
)
