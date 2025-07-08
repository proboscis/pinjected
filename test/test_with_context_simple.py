"""Tests for pinjected.with_context module."""

import pytest
from dataclasses import is_dataclass, fields

from pinjected.with_context import WithContext


class TestWithContext:
    """Test the WithContext dataclass."""

    def test_with_context_is_dataclass(self):
        """Test that WithContext is a dataclass."""
        assert is_dataclass(WithContext)

    def test_with_context_instantiation(self):
        """Test creating WithContext instance."""
        context = WithContext()
        assert context is not None
        assert isinstance(context, WithContext)

    def test_with_context_has_no_fields(self):
        """Test that WithContext has no fields."""
        context_fields = fields(WithContext)
        assert len(context_fields) == 0

    def test_with_context_equality(self):
        """Test WithContext equality."""
        context1 = WithContext()
        context2 = WithContext()

        # Empty dataclasses should be equal
        assert context1 == context2

    def test_with_context_repr(self):
        """Test WithContext string representation."""
        context = WithContext()
        assert repr(context) == "WithContext()"

    def test_with_context_hash(self):
        """Test WithContext is hashable."""
        context = WithContext()
        # Should not raise
        hash(context)

        # Can be used in sets
        context_set = {context, WithContext()}
        assert len(context_set) == 1  # Both are equal

    def test_multiple_instances(self):
        """Test creating multiple instances."""
        contexts = [WithContext() for _ in range(5)]

        # All should be equal
        for ctx in contexts:
            assert ctx == contexts[0]

    def test_module_imports(self):
        """Test that module can be imported."""
        import pinjected.with_context

        assert pinjected.with_context is not None
        assert hasattr(pinjected.with_context, "WithContext")

    def test_dataclass_import(self):
        """Test that dataclass is imported in module."""
        import pinjected.with_context
        import inspect

        # Check module has dataclass import
        source = inspect.getsource(pinjected.with_context)
        assert "from dataclasses import dataclass" in source


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
