"""Tests for pinjected.exception_util module."""

import pytest
from pinjected.exception_util import unwrap_exception_group
from pinjected.compatibility.task_group import CompatibleExceptionGroup


class TestUnwrapExceptionGroup:
    """Tests for unwrap_exception_group function."""

    def test_unwrap_single_exception_group(self):
        """Test unwrapping a single exception from an exception group."""
        inner_exc = ValueError("test error")
        exc_group = CompatibleExceptionGroup([inner_exc])

        result = unwrap_exception_group(exc_group)

        assert result is inner_exc
        assert isinstance(result, ValueError)
        assert str(result) == "test error"

    def test_unwrap_nested_exception_groups(self):
        """Test unwrapping nested exception groups."""
        inner_exc = RuntimeError("nested error")
        exc_group1 = CompatibleExceptionGroup([inner_exc])
        exc_group2 = CompatibleExceptionGroup([exc_group1])

        result = unwrap_exception_group(exc_group2)

        assert result is inner_exc
        assert isinstance(result, RuntimeError)
        assert str(result) == "nested error"

    def test_no_unwrap_for_multiple_exceptions(self):
        """Test that groups with multiple exceptions are not unwrapped."""
        exc1 = ValueError("error 1")
        exc2 = TypeError("error 2")
        exc_group = CompatibleExceptionGroup([exc1, exc2])

        result = unwrap_exception_group(exc_group)

        assert result is exc_group
        assert len(result.exceptions) == 2

    def test_no_unwrap_for_non_exception_group(self):
        """Test that non-exception groups are returned as-is."""
        exc = Exception("regular exception")

        result = unwrap_exception_group(exc)

        assert result is exc
        assert str(result) == "regular exception"

    def test_unwrap_deeply_nested_groups(self):
        """Test unwrapping deeply nested single-exception groups."""
        inner_exc = KeyError("deep error")
        exc_group = CompatibleExceptionGroup([inner_exc])

        for i in range(5):
            exc_group = CompatibleExceptionGroup([exc_group])

        result = unwrap_exception_group(exc_group)

        assert result is inner_exc
        assert isinstance(result, KeyError)
        assert str(result) == "'deep error'"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
