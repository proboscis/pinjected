"""Tests for pinjected.exception_util module."""

import pytest

from pinjected.exception_util import unwrap_exception_group
from pinjected.compatibility.task_group import CompatibleExceptionGroup


class TestUnwrapExceptionGroup:
    """Test the unwrap_exception_group function."""

    def test_unwrap_single_exception_group(self):
        """Test unwrapping a single exception group."""
        inner_exc = ValueError("Test error")
        exc_group = CompatibleExceptionGroup([inner_exc])

        result = unwrap_exception_group(exc_group)
        assert result is inner_exc
        assert isinstance(result, ValueError)
        assert str(result) == "Test error"

    def test_unwrap_nested_exception_groups(self):
        """Test unwrapping nested exception groups."""
        inner_exc = RuntimeError("Nested error")
        exc_group1 = CompatibleExceptionGroup([inner_exc])
        exc_group2 = CompatibleExceptionGroup([exc_group1])
        exc_group3 = CompatibleExceptionGroup([exc_group2])

        result = unwrap_exception_group(exc_group3)
        assert result is inner_exc
        assert isinstance(result, RuntimeError)
        assert str(result) == "Nested error"

    def test_no_unwrap_multiple_exceptions(self):
        """Test that groups with multiple exceptions are not unwrapped."""
        exc1 = ValueError("Error 1")
        exc2 = TypeError("Error 2")
        exc_group = CompatibleExceptionGroup([exc1, exc2])

        result = unwrap_exception_group(exc_group)
        assert result is exc_group
        assert isinstance(result, CompatibleExceptionGroup)
        assert len(result.exceptions) == 2

    def test_unwrap_regular_exception(self):
        """Test that regular exceptions are returned as-is."""
        exc = Exception("Regular exception")

        result = unwrap_exception_group(exc)
        assert result is exc
        assert str(result) == "Regular exception"

    def test_unwrap_empty_exception_group(self):
        """Test handling of empty exception group."""
        exc_group = CompatibleExceptionGroup([])

        result = unwrap_exception_group(exc_group)
        assert result is exc_group
        assert isinstance(result, CompatibleExceptionGroup)
        assert len(result.exceptions) == 0

    def test_unwrap_mixed_nesting(self):
        """Test unwrapping with mixed single and multiple exception groups."""
        inner_exc = IOError("IO error")
        exc_group1 = CompatibleExceptionGroup([inner_exc])
        exc_group2 = CompatibleExceptionGroup([exc_group1])

        # Add another exception to the outer group
        other_exc = KeyError("Key error")
        exc_group3 = CompatibleExceptionGroup([exc_group2, other_exc])

        result = unwrap_exception_group(exc_group3)
        # Should not unwrap because outer group has multiple exceptions
        assert result is exc_group3
        assert len(result.exceptions) == 2

    def test_unwrap_preserves_exception_attributes(self):
        """Test that exception attributes are preserved."""

        class CustomError(Exception):
            def __init__(self, message, code):
                super().__init__(message)
                self.code = code

        custom_exc = CustomError("Custom error", 42)
        exc_group = CompatibleExceptionGroup([custom_exc])

        result = unwrap_exception_group(exc_group)
        assert result is custom_exc
        assert result.code == 42
        assert str(result) == "Custom error"

    def test_unwrap_none(self):
        """Test handling of None input."""
        result = unwrap_exception_group(None)
        assert result is None

    def test_module_imports(self):
        """Test module imports."""
        import pinjected.exception_util

        assert hasattr(pinjected.exception_util, "unwrap_exception_group")
        assert callable(pinjected.exception_util.unwrap_exception_group)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
