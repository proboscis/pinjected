"""Simple tests for with_context.py module."""

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

    def test_with_context_hash(self):
        """Test that WithContext instances are not hashable by default."""
        ctx1 = WithContext()

        # Dataclasses without frozen=True are not hashable
        with pytest.raises(TypeError, match="unhashable type"):
            hash(ctx1)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
