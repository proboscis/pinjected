"""Comprehensive tests for with_context.py module."""

import pytest
from dataclasses import fields, is_dataclass

from pinjected.with_context import WithContext


class TestWithContext:
    """Test the WithContext dataclass."""

    def test_with_context_is_dataclass(self):
        """Test that WithContext is a dataclass."""
        assert is_dataclass(WithContext)

    def test_with_context_creation(self):
        """Test creating WithContext instance."""
        ctx = WithContext()
        assert isinstance(ctx, WithContext)

    def test_with_context_no_fields(self):
        """Test that WithContext has no fields."""
        ctx_fields = fields(WithContext)
        assert len(ctx_fields) == 0

    def test_with_context_equality(self):
        """Test WithContext equality (dataclass feature)."""
        ctx1 = WithContext()
        ctx2 = WithContext()
        # All instances should be equal since there are no fields
        assert ctx1 == ctx2

    def test_with_context_repr(self):
        """Test WithContext repr (dataclass feature)."""
        ctx = WithContext()
        repr_str = repr(ctx)
        assert repr_str == "WithContext()"

    def test_with_context_not_hashable(self):
        """Test that WithContext instances are not hashable by default."""
        ctx1 = WithContext()

        # Dataclasses without frozen=True are not hashable
        with pytest.raises(TypeError, match="unhashable type"):
            hash(ctx1)

    def test_with_context_mutable(self):
        """Test that WithContext instances are mutable."""
        ctx = WithContext()
        # Can add attributes dynamically
        ctx.custom_attr = "value"
        assert ctx.custom_attr == "value"

    def test_with_context_multiple_instances(self):
        """Test multiple WithContext instances."""
        contexts = [WithContext() for _ in range(5)]

        # All should be equal
        for i in range(1, 5):
            assert contexts[0] == contexts[i]

        # But they are different objects
        for i in range(1, 5):
            assert contexts[0] is not contexts[i]

    def test_with_context_as_parameter(self):
        """Test using WithContext as a function parameter."""

        def func_with_context(ctx: WithContext):
            assert isinstance(ctx, WithContext)
            return "success"

        result = func_with_context(WithContext())
        assert result == "success"

    def test_with_context_module_location(self):
        """Test WithContext is in the correct module."""
        assert WithContext.__module__ == "pinjected.with_context"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
