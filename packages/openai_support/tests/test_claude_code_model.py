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
            "sonnet",  # claude_model
            MagicMock(),  # logger
            prompt="Test prompt",
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
            "opus",  # claude_model
            MagicMock(),  # logger
            prompt="Test prompt",
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

    # Verify subprocess was called without model parameter
    mock_subprocess.assert_called_once_with(prompt="Test prompt")
    assert result == "Test response"


def test_claude_code_design_example():
    """Example of how to use different models via design override."""
    # To use different models with the Claude Code implementation,
    # you can override the claude_model dependency:
    #
    # Example 1: Create a resolver with sonnet model
    # sonnet_design = design(claude_model="sonnet")
    # resolver = Injected.resolver(sonnet_design)
    # sonnet_llm = await resolver.provide(a_sllm_claude_code)
    #
    # Example 2: Create a resolver with opus model (default)
    # opus_design = design(claude_model="opus")
    # resolver = Injected.resolver(opus_design)
    # opus_llm = await resolver.provide(a_sllm_claude_code)
    #
    # Example 3: Use with existing design
    # my_design = existing_design.merge(design(claude_model="sonnet"))

    # For this test, we just verify the imports work
    from pinjected_openai.claude_code import a_sllm_claude_code, claude_model

    assert a_sllm_claude_code is not None
    assert claude_model is not None
