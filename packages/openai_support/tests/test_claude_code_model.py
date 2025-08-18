"""Test model parameter for Claude Code implementation."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from pinjected_openai.claude_code import (
    a_claude_code_subprocess,
    a_sllm_claude_code,
)


@pytest.mark.asyncio
async def test_claude_code_subprocess_sonnet_model():
    """Test that sonnet model is passed correctly to CLI."""
    # Mock the subprocess
    mock_process = MagicMock()
    mock_process.returncode = 0
    mock_process.communicate = AsyncMock(return_value=(b"Test response", b""))

    with (
        patch(
            "asyncio.create_subprocess_exec", return_value=mock_process
        ) as mock_subprocess,
        patch("pathlib.Path.exists", return_value=True),
    ):
        # Call with sonnet model
        result = await a_claude_code_subprocess.src_function(
            "/usr/local/bin/claude",  # claude_command_path_str
            "/tmp",  # claude_code_working_dir
            MagicMock(),  # logger
            prompt="Test prompt",
            model="sonnet",
        )

        # Verify the command includes --model sonnet
        mock_subprocess.assert_called_once()
        args = mock_subprocess.call_args[0]
        assert "/usr/local/bin/claude" in args
        assert "-p" in args
        assert "--model" in args
        assert "sonnet" in args
        assert result == "Test response"


@pytest.mark.asyncio
async def test_claude_code_subprocess_opus_model():
    """Test that opus model is passed correctly to CLI."""
    # Mock the subprocess
    mock_process = MagicMock()
    mock_process.returncode = 0
    mock_process.communicate = AsyncMock(return_value=(b"Test response", b""))

    with (
        patch(
            "asyncio.create_subprocess_exec", return_value=mock_process
        ) as mock_subprocess,
        patch("pathlib.Path.exists", return_value=True),
    ):
        # Call with opus model (default)
        result = await a_claude_code_subprocess.src_function(
            "/usr/local/bin/claude",  # claude_command_path_str
            "/tmp",  # claude_code_working_dir
            MagicMock(),  # logger
            prompt="Test prompt",
            model="opus",
        )

        # Verify the command includes --model opus
        mock_subprocess.assert_called_once()
        args = mock_subprocess.call_args[0]
        assert "/usr/local/bin/claude" in args
        assert "-p" in args
        assert "--model" in args
        assert "opus" in args
        assert result == "Test response"


@pytest.mark.asyncio
async def test_sllm_claude_code_model_parameter():
    """Test that model parameter is passed through sllm interface."""
    mock_subprocess = AsyncMock(return_value="Test response")
    mock_structured = AsyncMock()

    # Test with default model from dependency injection
    result = await a_sllm_claude_code.src_function(
        mock_subprocess,  # a_claude_code_subprocess
        mock_structured,  # a_claude_code_structured
        MagicMock(),  # logger
        text="Test prompt",
    )

    # Verify subprocess was called with default model parameter
    mock_subprocess.assert_called_once_with(prompt="Test prompt", model="opus")
    assert result == "Test response"


def test_claude_code_design_example():
    """Example of how to use different models with Claude Code."""
    # To use different models with the Claude Code implementation,
    # pass the model parameter when calling the functions:
    #
    # Example 1: Use with sonnet model
    # result = await a_claude_code_subprocess(
    #     prompt="Test prompt",
    #     model="sonnet"
    # )
    #
    # Example 2: Use with opus model (default)
    # result = await a_claude_code_subprocess(
    #     prompt="Test prompt",
    #     model="opus"  # or omit for default
    # )
    #
    # Example 3: Use with StructuredLLM interface
    # sllm = await resolver.provide(a_sllm_claude_code)
    # result = await sllm("Test prompt", model="sonnet")

    # For this test, we just verify the imports work
    from pinjected_openai.claude_code import a_sllm_claude_code

    assert a_sllm_claude_code is not None
