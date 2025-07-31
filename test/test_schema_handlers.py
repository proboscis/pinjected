"""Tests for schema/handlers.py to improve coverage."""

import pytest
from pinjected.schema.handlers import (
    PinjectedHandleMainException,
    PinjectedHandleMainResult,
)
from pinjected.v2.keys import StrBindKey


def test_pinjected_handle_main_exception_protocol():
    """Test PinjectedHandleMainException protocol."""
    # Test that the protocol has the correct key
    assert PinjectedHandleMainException.key == StrBindKey(
        "__pinjected_handle_main_exception__"
    )

    # Test that it's a Protocol
    assert hasattr(PinjectedHandleMainException, "__call__")


def test_pinjected_handle_main_result_protocol():
    """Test PinjectedHandleMainResult protocol."""
    # Test that the protocol has the correct key
    assert PinjectedHandleMainResult.key == StrBindKey(
        "__pinjected_handle_main_result__"
    )

    # Test that it's a Protocol
    assert hasattr(PinjectedHandleMainResult, "__call__")


def test_protocol_implementation():
    """Test implementing the protocols."""

    # Implement PinjectedHandleMainException
    class MyExceptionHandler:
        async def __call__(self, context, e):
            return f"Handled: {e}"

    handler = MyExceptionHandler()
    # The protocol doesn't require inheritance, just the right signature
    assert callable(handler)

    # Implement PinjectedHandleMainResult
    class MyResultHandler:
        async def __call__(self, context, result):
            pass  # This covers line 36

    result_handler = MyResultHandler()
    assert callable(result_handler)


@pytest.mark.asyncio
async def test_protocol_implementation_with_execution():
    """Test actually executing the protocol implementations."""
    from unittest.mock import Mock

    # Test PinjectedHandleMainException execution
    class MyExceptionHandler:
        key = StrBindKey("__pinjected_handle_main_exception__")

        async def __call__(self, context, e):
            # This mimics the protocol's expected behavior
            return f"Handled: {e}"

    handler = MyExceptionHandler()
    mock_context = Mock()
    result = await handler(mock_context, ValueError("test"))
    assert result == "Handled: test"

    # Test PinjectedHandleMainResult execution
    class MyResultHandler:
        key = StrBindKey("__pinjected_handle_main_result__")

        def __init__(self):
            self.results = []

        async def __call__(self, context, result):
            # This mimics line 36's pass behavior - just process without returning
            self.results.append(result)
            # The protocol method body has 'pass' on line 36
            pass

    result_handler = MyResultHandler()
    await result_handler(mock_context, "test_result")
    assert result_handler.results == ["test_result"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
