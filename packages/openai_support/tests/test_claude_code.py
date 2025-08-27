"""Tests for Claude Code subprocess implementation of StructuredLLM."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from pydantic import BaseModel

from pinjected_openai.claude_code import (
    ClaudeCodeError,
    ClaudeCodeNotFoundError,
    ClaudeCodeTimeoutError,
    ClaudeCodeCreditBalanceError,
)


class MockResponse(BaseModel):
    message: str
    status: str


@pytest.mark.asyncio
async def test_claude_code_subprocess_plain_text():
    """Test plain text response from Claude Code subprocess."""
    from pinjected_openai.claude_code import a_claude_code_subprocess

    with (
        patch("asyncio.create_subprocess_exec") as mock_subprocess,
        patch("pathlib.Path.exists", return_value=True),
    ):
        # Mock process
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"Tokyo", b""))
        mock_subprocess.return_value = mock_process

        # Import the actual decorated function and call it
        mock_logger = Mock()
        result = await a_claude_code_subprocess.src_function(
            "claude",  # claude_command_path_str
            "/tmp",  # claude_code_working_dir
            mock_logger,
            prompt="What is the capital of Japan?",
            model="opus",
        )
        assert result == "Tokyo"

        # Verify subprocess was called correctly
        mock_subprocess.assert_called_once()
        args = mock_subprocess.call_args[0]
        # The first argument should be either a full path or "claude"
        assert args[0].endswith("claude") or args[0] == "claude"
        assert args[1] == "-p"
        assert "--model" in args
        assert "opus" in args
        # Check that cwd was passed
        kwargs = mock_subprocess.call_args[1]
        assert "cwd" in kwargs
        assert kwargs["cwd"] == "/tmp"


@pytest.mark.asyncio
async def test_claude_code_subprocess_error():
    """Test error handling in Claude Code subprocess."""
    from pinjected_openai.claude_code import a_claude_code_subprocess

    with (
        patch("asyncio.create_subprocess_exec") as mock_subprocess,
        patch("pathlib.Path.exists", return_value=True),
    ):
        # Mock process with error
        mock_process = MagicMock()
        mock_process.returncode = 1
        mock_process.communicate = AsyncMock(
            return_value=(b"", b"Error: API key not found")
        )
        mock_subprocess.return_value = mock_process

        mock_logger = Mock()

        with pytest.raises(ClaudeCodeError) as exc_info:
            await a_claude_code_subprocess.src_function(
                "claude", "/tmp", mock_logger, prompt="Test prompt", model="opus"
            )

        assert "Claude Code failed" in str(exc_info.value)
        assert "stderr: Error: API key not found" in str(exc_info.value)


@pytest.mark.asyncio
async def test_claude_code_subprocess_error_with_stdout_only():
    """Test error handling when only stdout is present."""
    from pinjected_openai.claude_code import a_claude_code_subprocess

    with (
        patch("asyncio.create_subprocess_exec") as mock_subprocess,
        patch("pathlib.Path.exists", return_value=True),
    ):
        # Mock process with error and stdout only
        mock_process = MagicMock()
        mock_process.returncode = 1
        mock_process.communicate = AsyncMock(
            return_value=(b"Some error output in stdout", b"")
        )
        mock_subprocess.return_value = mock_process

        mock_logger = Mock()

        with pytest.raises(ClaudeCodeError) as exc_info:
            await a_claude_code_subprocess.src_function(
                "claude", "/tmp", mock_logger, prompt="Test prompt", model="opus"
            )

        assert "Claude Code failed" in str(exc_info.value)
        assert "stdout: Some error output in stdout" in str(exc_info.value)


@pytest.mark.asyncio
async def test_claude_code_subprocess_error_with_both_outputs():
    """Test error handling when both stdout and stderr are present."""
    from pinjected_openai.claude_code import a_claude_code_subprocess

    with (
        patch("asyncio.create_subprocess_exec") as mock_subprocess,
        patch("pathlib.Path.exists", return_value=True),
    ):
        # Mock process with error and both outputs
        mock_process = MagicMock()
        mock_process.returncode = 1
        mock_process.communicate = AsyncMock(
            return_value=(b"Stdout message", b"Stderr message")
        )
        mock_subprocess.return_value = mock_process

        mock_logger = Mock()

        with pytest.raises(ClaudeCodeError) as exc_info:
            await a_claude_code_subprocess.src_function(
                "claude", "/tmp", mock_logger, prompt="Test prompt", model="opus"
            )

        error_str = str(exc_info.value)
        assert "Claude Code failed" in error_str
        assert "stderr: Stderr message" in error_str
        assert "stdout: Stdout message" in error_str
        # Verify both are included with separator
        assert " | " in error_str


@pytest.mark.asyncio
async def test_claude_code_subprocess_credit_balance_error():
    """Test that credit balance errors are raised as specific exception."""
    from pinjected_openai.claude_code import a_claude_code_subprocess

    with (
        patch("asyncio.create_subprocess_exec") as mock_subprocess,
        patch("pathlib.Path.exists", return_value=True),
    ):
        # Mock process with credit balance error
        mock_process = MagicMock()
        mock_process.returncode = 1
        mock_process.communicate = AsyncMock(
            return_value=(b"Credit balance is too low", b"")
        )
        mock_subprocess.return_value = mock_process

        mock_logger = Mock()

        with pytest.raises(ClaudeCodeCreditBalanceError) as exc_info:
            await a_claude_code_subprocess.src_function(
                "claude", "/tmp", mock_logger, prompt="Test prompt", model="opus"
            )

        assert "Credit balance is too low" in str(exc_info.value)


@pytest.mark.asyncio
async def test_claude_code_subprocess_timeout():
    """Test timeout handling in Claude Code subprocess."""
    from pinjected_openai.claude_code import a_claude_code_subprocess

    with (
        patch("asyncio.create_subprocess_exec") as mock_subprocess,
        patch("pathlib.Path.exists", return_value=True),
    ):
        # Mock process that times out
        mock_process = MagicMock()
        mock_process.communicate = AsyncMock(side_effect=asyncio.TimeoutError())
        mock_subprocess.return_value = mock_process

        mock_logger = Mock()

        with pytest.raises(ClaudeCodeTimeoutError) as exc_info:
            await a_claude_code_subprocess.src_function(
                "claude",
                "/tmp",
                mock_logger,
                prompt="Test prompt",
                model="opus",
                timeout=1.0,
            )

        assert "timed out" in str(exc_info.value)


@pytest.mark.asyncio
async def test_claude_code_subprocess_not_found():
    """Test handling when Claude Code command is not found."""
    from pinjected_openai.claude_code import a_claude_code_subprocess

    with patch("pathlib.Path.exists", return_value=False):
        mock_logger = Mock()

        with pytest.raises(ClaudeCodeNotFoundError) as exc_info:
            await a_claude_code_subprocess.src_function(
                "/path/to/nonexistent/claude",
                "/tmp",
                mock_logger,
                prompt="Test prompt",
                model="opus",
            )

        assert "command not found" in str(exc_info.value)
        assert "/path/to/nonexistent/claude" in str(exc_info.value)


@pytest.mark.asyncio
async def test_claude_code_structured():
    """Test structured response parsing."""
    from pinjected_openai.claude_code import a_claude_code_structured

    mock_subprocess = AsyncMock(return_value='{"message": "Hello", "status": "ok"}')
    mock_logger = Mock()

    result = await a_claude_code_structured.src_function(
        mock_subprocess,
        mock_logger,
        prompt="Test prompt",
        response_format=MockResponse,
    )

    assert isinstance(result, MockResponse)
    assert result.message == "Hello"
    assert result.status == "ok"

    # Verify the prompt was modified to include schema
    call_args = mock_subprocess.call_args[1]
    assert "JSON object" in call_args["prompt"]
    assert "schema" in call_args["prompt"]


@pytest.mark.asyncio
async def test_claude_code_structured_with_markdown():
    """Test structured response parsing with markdown code blocks."""
    from pinjected_openai.claude_code import a_claude_code_structured

    mock_subprocess = AsyncMock(
        return_value='```json\n{"message": "Hello", "status": "ok"}\n```'
    )
    mock_logger = Mock()

    result = await a_claude_code_structured.src_function(
        mock_subprocess,
        mock_logger,
        prompt="Test prompt",
        response_format=MockResponse,
    )

    assert isinstance(result, MockResponse)
    assert result.message == "Hello"
    assert result.status == "ok"


@pytest.mark.asyncio
async def test_claude_code_structured_with_json_repair():
    """Test structured response parsing with JSON repair fallback."""
    from pinjected_openai.claude_code import a_claude_code_structured

    # Invalid JSON (missing closing quote)
    mock_subprocess = AsyncMock(return_value='{"message": "Hello, "status": "ok"}')
    mock_logger = Mock()

    # json_repair should fix the invalid JSON
    result = await a_claude_code_structured.src_function(
        mock_subprocess,
        mock_logger,
        prompt="Test prompt",
        response_format=MockResponse,
    )

    assert isinstance(result, MockResponse)
    assert "Hello" in result.message
    assert result.status == "ok"


@pytest.mark.asyncio
async def test_claude_code_structured_with_retry_fix():
    """Test structured response parsing with retry mechanism when initial response fails."""
    from pinjected_openai.claude_code import a_claude_code_structured

    # Mock subprocess to fail first time, then succeed with fixed JSON
    mock_subprocess = AsyncMock(
        side_effect=[
            "Execution error",  # First attempt fails
            '{"message": "Fixed on retry", "status": "success"}',  # Second attempt succeeds
        ]
    )
    mock_logger = Mock()

    result = await a_claude_code_structured.src_function(
        mock_subprocess,
        mock_logger,
        prompt="Test prompt",
        response_format=MockResponse,
    )

    assert isinstance(result, MockResponse)
    assert result.message == "Fixed on retry"
    assert result.status == "success"

    # Verify subprocess was called twice (initial + 1 retry)
    assert mock_subprocess.call_count == 2

    # Check the retry prompt contains fix instructions
    second_call_prompt = mock_subprocess.call_args_list[1][1]["prompt"]
    assert "failed to produce valid JSON" in second_call_prompt
    assert "Previous attempts and their errors:" in second_call_prompt
    assert "Execution error" in second_call_prompt  # The failed response
    assert "Error:" in second_call_prompt  # The error details
    assert "Test prompt" in second_call_prompt  # Original request
    assert "IMPORTANT:" in second_call_prompt  # Additional instructions


@pytest.mark.asyncio
async def test_sllm_claude_code_plain():
    """Test StructuredLLM implementation with plain text."""
    from pinjected_openai.claude_code import a_sllm_claude_code

    mock_subprocess = AsyncMock(return_value="Tokyo")
    mock_structured = AsyncMock()
    mock_logger = Mock()

    # Mock the contextualize method
    mock_context = MagicMock()
    mock_context.__enter__ = MagicMock(return_value=None)
    mock_context.__exit__ = MagicMock(return_value=None)
    mock_logger.contextualize = MagicMock(return_value=mock_context)

    # Get the actual function from the decorator wrapper
    actual_func = a_sllm_claude_code
    # Find the wrapped function - tenacity wraps it
    while hasattr(actual_func, "__wrapped__"):
        actual_func = actual_func.__wrapped__

    result = await actual_func.src_function(
        mock_subprocess,
        mock_structured,
        mock_logger,
        text="What is the capital of Japan?",
    )

    assert result == "Tokyo"
    mock_subprocess.assert_called_once_with(
        prompt="What is the capital of Japan?", model="opus"
    )
    mock_structured.assert_not_called()


@pytest.mark.asyncio
async def test_sllm_claude_code_structured():
    """Test StructuredLLM implementation with structured output."""
    from pinjected_openai.claude_code import a_sllm_claude_code

    mock_subprocess = AsyncMock()
    mock_structured = AsyncMock(
        return_value=MockResponse(message="Tokyo", status="confident")
    )
    mock_logger = Mock()

    # Mock the contextualize method
    mock_context = MagicMock()
    mock_context.__enter__ = MagicMock(return_value=None)
    mock_context.__exit__ = MagicMock(return_value=None)
    mock_logger.contextualize = MagicMock(return_value=mock_context)

    # Get the actual function from the decorator wrapper
    actual_func = a_sllm_claude_code
    while hasattr(actual_func, "__wrapped__"):
        actual_func = actual_func.__wrapped__

    result = await actual_func.src_function(
        mock_subprocess,
        mock_structured,
        mock_logger,
        text="What is the capital of Japan?",
        response_format=MockResponse,
    )

    assert isinstance(result, MockResponse)
    assert result.message == "Tokyo"
    assert result.status == "confident"

    mock_subprocess.assert_not_called()
    mock_structured.assert_called_once_with(
        prompt="What is the capital of Japan?",
        response_format=MockResponse,
        model="opus",
    )


@pytest.mark.asyncio
async def test_sllm_claude_code_credit_balance_retry():
    """Test that credit balance errors trigger retries."""
    from pinjected_openai.claude_code import a_sllm_claude_code

    mock_subprocess = AsyncMock(
        side_effect=[
            ClaudeCodeCreditBalanceError(
                "Claude Code failed: stdout: Credit balance is too low"
            ),
            ClaudeCodeCreditBalanceError(
                "Claude Code failed: stdout: Credit balance is too low"
            ),
            "Success on third attempt",  # Succeeds on third try
        ]
    )
    mock_structured = AsyncMock()
    mock_logger = Mock()

    # Mock the contextualize method
    mock_context = MagicMock()
    mock_context.__enter__ = MagicMock(return_value=None)
    mock_context.__exit__ = MagicMock(return_value=None)
    mock_logger.contextualize = MagicMock(return_value=mock_context)

    # Get the actual function from the decorator wrapper
    actual_func = a_sllm_claude_code
    while hasattr(actual_func, "__wrapped__"):
        actual_func = actual_func.__wrapped__

    result = await actual_func.src_function(
        mock_subprocess,
        mock_structured,
        mock_logger,
        text="Test prompt",
    )

    assert result == "Success on third attempt"
    assert mock_subprocess.call_count == 3
    # Verify warning was logged for credit balance error
    mock_logger.warning.assert_called()
    assert "Credit balance error" in mock_logger.warning.call_args[0][0]


@pytest.mark.asyncio
async def test_sllm_claude_code_non_credit_error_no_retry():
    """Test that non-credit balance errors do NOT trigger retries."""
    from pinjected_openai.claude_code import a_sllm_claude_code

    mock_subprocess = AsyncMock(
        side_effect=ClaudeCodeError("Claude Code failed: Some other error")
    )
    mock_structured = AsyncMock()
    mock_logger = Mock()

    # Mock the contextualize method
    mock_context = MagicMock()
    mock_context.__enter__ = MagicMock(return_value=None)
    mock_context.__exit__ = MagicMock(return_value=None)
    mock_logger.contextualize = MagicMock(return_value=mock_context)

    # Get the actual function from the decorator wrapper
    actual_func = a_sllm_claude_code
    while hasattr(actual_func, "__wrapped__"):
        actual_func = actual_func.__wrapped__

    with pytest.raises(ClaudeCodeError) as exc_info:
        await actual_func.src_function(
            mock_subprocess,
            mock_structured,
            mock_logger,
            text="Test prompt",
        )

    # Should fail immediately without retries
    assert mock_subprocess.call_count == 1
    assert "Some other error" in str(exc_info.value)
    # Verify error was logged (not warning)
    mock_logger.error.assert_called()
    assert "Claude Code error" in mock_logger.error.call_args[0][0]


@pytest.mark.asyncio
async def test_sllm_claude_code_with_images_warning():
    """Test that images trigger a warning."""
    from pinjected_openai.claude_code import a_sllm_claude_code

    mock_logger = Mock()
    mock_subprocess = AsyncMock(return_value="Response")
    mock_structured = AsyncMock()

    # Mock the contextualize method
    mock_context = MagicMock()
    mock_context.__enter__ = MagicMock(return_value=None)
    mock_context.__exit__ = MagicMock(return_value=None)
    mock_logger.contextualize = MagicMock(return_value=mock_context)

    # Get the actual function from the decorator wrapper
    actual_func = a_sllm_claude_code
    while hasattr(actual_func, "__wrapped__"):
        actual_func = actual_func.__wrapped__

    result = await actual_func.src_function(
        mock_subprocess,
        mock_structured,
        mock_logger,
        text="Test",
        images=["fake_image"],
    )

    assert result == "Response"
    # Verify warning was logged
    mock_logger.warning.assert_called()
    assert "not currently supported" in mock_logger.warning.call_args[0][0]
