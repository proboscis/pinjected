"""Tests for OpenRouter utility functions, specifically retry logic and error handling."""

from unittest.mock import MagicMock
import pytest
from pinjected_openai.openrouter.util import (
    handle_openrouter_error,
    build_provider_filter,
    build_user_message,
    build_chat_payload,
    log_completion_cost,
    validate_response_format,
    OpenRouterRateLimitError,
    OpenRouterTimeOutError,
    OpenRouterOverloadedError,
    OpenRouterTransientError,
)
from pydantic import BaseModel


def test_handle_429_rate_limit_error():
    """Test that 429 error code properly raises OpenRouterRateLimitError."""
    logger = MagicMock()

    # Test with explicit 429 error code
    error_response = {
        "error": {
            "code": 429,
            "message": "Provider returned error",
            "metadata": {
                "provider_name": "Stealth",
                "raw": "openrouter/horizon-beta is temporarily rate-limited upstream",
            },
        }
    }

    with pytest.raises(OpenRouterRateLimitError):
        handle_openrouter_error(error_response, logger)

    # Verify logger was called
    logger.warning.assert_called_once()


def test_handle_rate_limit_in_message():
    """Test that rate-limited string in message raises OpenRouterRateLimitError."""
    logger = MagicMock()

    # Test with rate-limited in message
    error_response = {
        "error": {"message": "Model is temporarily rate-limited, please retry"}
    }

    with pytest.raises(OpenRouterRateLimitError):
        handle_openrouter_error(error_response, logger)


def test_handle_timeout_error():
    """Test that timeout errors raise OpenRouterTimeOutError."""
    logger = MagicMock()

    error_response = {"error": {"message": "Request Timed out waiting for response"}}

    with pytest.raises(OpenRouterTimeOutError):
        handle_openrouter_error(error_response, logger)


def test_handle_overloaded_error():
    """Test that overloaded/502 errors raise OpenRouterOverloadedError."""
    logger = MagicMock()

    # Test with 502 error code
    error_response = {"error": {"code": 502, "message": "Bad Gateway"}}

    with pytest.raises(OpenRouterOverloadedError):
        handle_openrouter_error(error_response, logger)

    # Test with Overloaded in message
    error_response = {"error": {"message": "Service Overloaded, please retry"}}

    with pytest.raises(OpenRouterOverloadedError):
        handle_openrouter_error(error_response, logger)


def test_handle_transient_error():
    """Test that transient errors (520, 503, 522, 524) raise OpenRouterTransientError."""
    logger = MagicMock()

    # Test each transient error code
    for code in [520, 503, 522, 524]:
        error_response = {"error": {"code": code, "message": f"Error {code}"}}

        with pytest.raises(OpenRouterTransientError):
            handle_openrouter_error(error_response, logger)


def test_handle_generic_error():
    """Test that generic errors raise RuntimeError."""
    logger = MagicMock()

    error_response = {"error": {"code": 400, "message": "Bad request"}}

    with pytest.raises(RuntimeError) as exc_info:
        handle_openrouter_error(error_response, logger)

    assert "Error in response" in str(exc_info.value)


def test_build_provider_filter():
    """Test provider filter building."""
    # Test with None provider
    assert build_provider_filter(None) == {}

    # Test with provider dict
    provider = {"name": "openai", "order": ["gpt-4"]}
    assert build_provider_filter(provider) == {"provider": provider}


def test_build_user_message():
    """Test user message building."""
    # Test without images
    msg = build_user_message("Hello")
    assert msg == {"role": "user", "content": [{"type": "text", "text": "Hello"}]}

    # Test with images would require PIL.Image mock


def test_build_chat_payload():
    """Test chat payload building."""
    payload = build_chat_payload(
        model="gpt-4",
        prompt="Hello",
        max_tokens=100,
        temperature=0.7,
        provider={"name": "openai"},
        include_reasoning=True,
        reasoning={"prompt": "Think step by step"},
    )

    assert payload["model"] == "gpt-4"
    assert payload["max_tokens"] == 100
    assert payload["temperature"] == 0.7
    assert payload["include_reasoning"] is True
    assert payload["reasoning"] == {"prompt": "Think step by step"}
    assert "provider" in payload


def test_validate_response_format():
    """Test response format validation."""

    class SimpleModel(BaseModel):
        name: str
        age: int

    # Should not raise for valid model
    validate_response_format(SimpleModel, "gpt-4")

    # Would need more complex models to test OpenAPI3/Gemini compatibility errors


def test_log_completion_cost():
    """Test cost logging function."""
    logger = MagicMock()
    openrouter_model_table = MagicMock()
    openrouter_state = {"cumulative_cost": 10.0}

    # Mock pricing and cost calculation
    mock_pricing = MagicMock()
    mock_pricing.calc_cost_dict.return_value = {"prompt": 0.5, "completion": 0.5}
    openrouter_model_table.safe_pricing.return_value.bind.return_value.value_or.return_value = {
        "prompt": 0.5,
        "completion": 0.5,
    }

    res = {
        "usage": {"prompt_tokens": 100, "completion_tokens": 50},
        "provider": "openai",
    }

    log_completion_cost(res, "gpt-4", openrouter_model_table, openrouter_state, logger)

    # Verify logger was called with cost info
    logger.info.assert_called_once()
    assert "cumulative cost: 11.0" in logger.info.call_args[0][0]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
