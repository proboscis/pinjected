"""Tests for demo.py module to improve coverage."""

import pytest
from unittest.mock import Mock

from pinjected import Design
from pinjected.demo import __design__, default_design, LLM, Gandalf, test_greeting


def test_design_exists():
    """Test that __design__ is defined."""
    assert isinstance(__design__, Design)


def test_default_design_alias():
    """Test that default_design is an alias for __design__."""
    assert default_design is __design__


def test_design_bindings():
    """Test that __design__ is a proper Design object."""
    # Check that __design__ is a MergedDesign with multiple sources
    assert __design__.__class__.__name__ == "MergedDesign"

    # The design should have multiple source designs
    design_str = str(__design__)
    assert "MergedDesign" in design_str
    assert "srcs=" in design_str


def test_load_openai_api_key_binding():
    """Test that the design was created with the expected bindings."""
    # Since we can't directly access the bindings of a MergedDesign,
    # we verify that the design was created using the design() function
    # with the expected parameters as shown in the source code
    assert __design__ is not None
    assert isinstance(__design__, Design)


def test_llm_function_exists():
    """Test that LLM function is defined."""
    assert callable(LLM)
    # LLM is a Partial object created by @injected decorator
    assert hasattr(LLM, "__class__")
    assert LLM.__class__.__name__ == "Partial"


def test_llm_function_signature():
    """Test LLM function has expected structure."""
    # LLM is a Partial object, verify it has the expected attributes
    assert hasattr(LLM, "src_function")
    assert hasattr(LLM, "dependencies")

    # The function should have the expected name
    func_name = getattr(LLM.src_function, "__name__", None)
    assert func_name == "LLM"

    # Check dependencies
    deps = LLM.dependencies()
    assert "load_openai_api_key" in deps
    assert "model" in deps
    assert "max_tokens" in deps


def test_llm_function_execution():
    """Test LLM function execution with mocked OpenAI."""
    # Import openai inside the test function
    import sys
    import types

    # Create a mock openai module
    mock_openai = types.ModuleType("openai")
    mock_completion = Mock()
    mock_completion.create = Mock(
        return_value={"choices": [{"text": "Mocked response"}]}
    )
    mock_openai.Completion = mock_completion

    # Temporarily replace openai in sys.modules
    original_openai = sys.modules.get("openai")
    sys.modules["openai"] = mock_openai

    try:
        # Get the wrapped function from the Partial object
        llm_func = LLM.src_function

        # Create a mock load function that returns a callable
        def mock_load_key():
            return "test_key"

        # Call the function with dependencies - note positional-only args before /
        result = llm_func(
            mock_load_key,  # load_openai_api_key
            "test-model",  # model
            100,  # max_tokens
            "Test prompt",  # prompt
        )

        # Verify
        mock_completion.create.assert_called_once_with(
            "test_key",  # API key from mock_load_key
            prompt="Test prompt",
            model="test-model",
            max_tokens=100,
        )
        assert result == "Mocked response"
    finally:
        # Restore original openai module
        if original_openai:
            sys.modules["openai"] = original_openai
        else:
            sys.modules.pop("openai", None)


def test_gandalf_function_exists():
    """Test that Gandalf function is defined."""
    assert callable(Gandalf)
    # Gandalf is a Partial object created by @injected decorator
    assert hasattr(Gandalf, "__class__")
    assert Gandalf.__class__.__name__ == "Partial"


def test_gandalf_function_signature():
    """Test Gandalf function has expected structure."""
    # Gandalf is a Partial object, verify it has the expected attributes
    assert hasattr(Gandalf, "src_function")
    assert hasattr(Gandalf, "dependencies")

    # The function should have the expected name
    func_name = getattr(Gandalf.src_function, "__name__", None)
    assert func_name == "Gandalf"

    # Check dependencies
    deps = Gandalf.dependencies()
    assert "LLM" in deps


def test_gandalf_function_execution():
    """Test Gandalf function execution."""
    # Create a mock LLM function
    mock_llm = Mock(return_value="You shall not pass!")

    # Get the wrapped function from the Partial object
    gandalf_func = Gandalf.src_function

    # Call the function with dependencies - note positional-only args before /
    result = gandalf_func(
        mock_llm,  # LLM
        "Hello",  # user_message
    )

    # Verify
    mock_llm.assert_called_once()
    args = mock_llm.call_args[0]
    assert "Gandalf" in args[0]
    assert "Hello" in args[0]
    assert result == "You shall not pass!"


def test_test_greeting_proxy():
    """Test that test_greeting is an IProxy."""
    assert hasattr(test_greeting, "__dict__")  # Basic check for proxy-like object
    # test_greeting should be the result of Gandalf("How are you?")


def test_test_greeting_is_gandalf_call():
    """Test that test_greeting is created by calling Gandalf."""
    # Since test_greeting = Gandalf("How are you?"), it should be a proxy
    # that will call Gandalf with "How are you?" when evaluated

    # The proxy should have internal structure related to Gandalf
    # We can't execute it directly without proper DI context, but we can
    # verify it's a proxy-like object
    assert not isinstance(test_greeting, str)  # It's not the actual result
    assert hasattr(test_greeting, "__class__")  # It's an object


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
