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
        """Test that WithContext instances are hashable (frozen=True)."""
        ctx1 = WithContext()
        ctx2 = WithContext()

        # Dataclasses with frozen=True are hashable
        assert hash(ctx1) == hash(ctx2)  # Same instances should have same hash

        # Can be used in sets and dicts
        assert {ctx1, ctx2} == {ctx1}  # They are equal, so set has one element
        assert {ctx1: "value"}[ctx2] == "value"  # Can use as dict key


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
