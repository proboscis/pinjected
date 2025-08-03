"""Tests for Claude Code subprocess implementation of StructuredLLM."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pydantic import BaseModel

from pinjected_openai.claude_code import (
    ClaudeCodeError,
    ClaudeCodeNotFoundError,
    ClaudeCodeTimeoutError,
    a_claude_code_subprocess,
    a_claude_code_structured,
    a_sllm_claude_code,
)
from pinjected import Injected


class TestResponse(BaseModel):
    message: str
    status: str


@pytest.mark.asyncio
async def test_claude_code_subprocess_plain_text():
    """Test plain text response from Claude Code subprocess."""
    mock_logger = MagicMock()

    with patch("asyncio.create_subprocess_exec") as mock_subprocess:
        # Mock process
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"Tokyo", b""))
        mock_subprocess.return_value = mock_process

        # Create function with injected dependencies
        func = Injected.bind(a_claude_code_subprocess, logger=mock_logger)

        result = await func("What is the capital of Japan?")
        assert result == "Tokyo"

        # Verify subprocess was called correctly
        mock_subprocess.assert_called_once()
        args = mock_subprocess.call_args[0]
        assert args[:2] == ("claude", "-p")


@pytest.mark.asyncio
async def test_claude_code_subprocess_error():
    """Test error handling in Claude Code subprocess."""
    mock_logger = MagicMock()

    with patch("asyncio.create_subprocess_exec") as mock_subprocess:
        # Mock process with error
        mock_process = MagicMock()
        mock_process.returncode = 1
        mock_process.communicate = AsyncMock(
            return_value=(b"", b"Error: API key not found")
        )
        mock_subprocess.return_value = mock_process

        func = Injected.bind(a_claude_code_subprocess, logger=mock_logger)

        with pytest.raises(ClaudeCodeError) as exc_info:
            await func("Test prompt")

        assert "Claude Code failed" in str(exc_info.value)


@pytest.mark.asyncio
async def test_claude_code_subprocess_timeout():
    """Test timeout handling in Claude Code subprocess."""
    mock_logger = MagicMock()

    with patch("asyncio.create_subprocess_exec") as mock_subprocess:
        # Mock process that times out
        mock_process = MagicMock()
        mock_process.communicate = AsyncMock(side_effect=asyncio.TimeoutError())
        mock_subprocess.return_value = mock_process

        func = Injected.bind(a_claude_code_subprocess, logger=mock_logger)

        with pytest.raises(ClaudeCodeTimeoutError) as exc_info:
            await func("Test prompt", timeout=1.0)

        assert "timed out" in str(exc_info.value)


@pytest.mark.asyncio
async def test_claude_code_subprocess_not_found():
    """Test handling when Claude Code command is not found."""
    mock_logger = MagicMock()

    with patch("asyncio.create_subprocess_exec") as mock_subprocess:
        mock_subprocess.side_effect = FileNotFoundError()

        func = Injected.bind(a_claude_code_subprocess, logger=mock_logger)

        with pytest.raises(ClaudeCodeNotFoundError) as exc_info:
            await func("Test prompt")

        assert "command not found" in str(exc_info.value)
        assert "npm install" in str(exc_info.value)


@pytest.mark.asyncio
async def test_claude_code_structured():
    """Test structured response parsing."""
    mock_logger = MagicMock()
    mock_subprocess = AsyncMock(return_value='{"message": "Hello", "status": "ok"}')

    func = Injected.bind(
        a_claude_code_structured,
        a_claude_code_subprocess=mock_subprocess,
        logger=mock_logger,
    )

    result = await func("Test prompt", response_format=TestResponse)

    assert isinstance(result, TestResponse)
    assert result.message == "Hello"
    assert result.status == "ok"

    # Verify the prompt was modified to include schema
    call_args = mock_subprocess.call_args[1]
    assert "JSON object" in call_args["prompt"]
    assert "schema" in call_args["prompt"]


@pytest.mark.asyncio
async def test_claude_code_structured_with_markdown():
    """Test structured response parsing with markdown code blocks."""
    mock_logger = MagicMock()
    mock_subprocess = AsyncMock(
        return_value='```json\n{"message": "Hello", "status": "ok"}\n```'
    )

    func = Injected.bind(
        a_claude_code_structured,
        a_claude_code_subprocess=mock_subprocess,
        logger=mock_logger,
    )

    result = await func("Test prompt", response_format=TestResponse)

    assert isinstance(result, TestResponse)
    assert result.message == "Hello"
    assert result.status == "ok"


@pytest.mark.asyncio
async def test_claude_code_structured_with_json_repair():
    """Test structured response parsing with JSON repair fallback."""
    mock_logger = MagicMock()
    # Invalid JSON (missing closing quote)
    mock_subprocess = AsyncMock(return_value='{"message": "Hello, "status": "ok"}')

    func = Injected.bind(
        a_claude_code_structured,
        a_claude_code_subprocess=mock_subprocess,
        logger=mock_logger,
    )

    # json_repair should fix the invalid JSON
    result = await func("Test prompt", response_format=TestResponse)

    assert isinstance(result, TestResponse)
    assert "Hello" in result.message
    assert result.status == "ok"


@pytest.mark.asyncio
async def test_sllm_claude_code_plain():
    """Test StructuredLLM implementation with plain text."""
    mock_logger = MagicMock()
    mock_subprocess = AsyncMock(return_value="Tokyo")
    mock_structured = AsyncMock()

    func = Injected.bind(
        a_sllm_claude_code,
        a_claude_code_subprocess=mock_subprocess,
        a_claude_code_structured=mock_structured,
        logger=mock_logger,
    )

    result = await func("What is the capital of Japan?")

    assert result == "Tokyo"
    mock_subprocess.assert_called_once_with(prompt="What is the capital of Japan?")
    mock_structured.assert_not_called()


@pytest.mark.asyncio
async def test_sllm_claude_code_structured():
    """Test StructuredLLM implementation with structured output."""
    mock_logger = MagicMock()
    mock_subprocess = AsyncMock()
    mock_structured = AsyncMock(
        return_value=TestResponse(message="Tokyo", status="confident")
    )

    func = Injected.bind(
        a_sllm_claude_code,
        a_claude_code_subprocess=mock_subprocess,
        a_claude_code_structured=mock_structured,
        logger=mock_logger,
    )

    result = await func("What is the capital of Japan?", response_format=TestResponse)

    assert isinstance(result, TestResponse)
    assert result.message == "Tokyo"
    assert result.status == "confident"

    mock_subprocess.assert_not_called()
    mock_structured.assert_called_once_with(
        prompt="What is the capital of Japan?", response_format=TestResponse
    )


@pytest.mark.asyncio
async def test_sllm_claude_code_with_images_warning():
    """Test that images trigger a warning."""
    mock_logger = MagicMock()
    mock_subprocess = AsyncMock(return_value="Response")
    mock_structured = AsyncMock()

    func = Injected.bind(
        a_sllm_claude_code,
        a_claude_code_subprocess=mock_subprocess,
        a_claude_code_structured=mock_structured,
        logger=mock_logger,
    )

    result = await func("Test", images=["fake_image"])

    assert result == "Response"
    # Verify warning was logged
    mock_logger.warning.assert_called()
    assert "not currently supported" in mock_logger.warning.call_args[0][0]


@pytest.mark.asyncio
async def test_sllm_claude_code_retry_on_timeout():
    """Test retry logic on timeout."""
    mock_logger = MagicMock()
    mock_subprocess = AsyncMock()
    mock_structured = AsyncMock()

    # First call times out, second succeeds
    mock_subprocess.side_effect = [ClaudeCodeTimeoutError("Timeout"), "Success"]

    func = Injected.bind(
        a_sllm_claude_code,
        a_claude_code_subprocess=mock_subprocess,
        a_claude_code_structured=mock_structured,
        logger=mock_logger,
    )

    result = await func("Test prompt")

    assert result == "Success"
    assert mock_subprocess.call_count == 2
