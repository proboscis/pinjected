"""Simple tests for maybe_patch.py module."""

import pytest
from returns.maybe import Maybe, Some, Nothing
from expression import Nothing as ExprNothing

from pinjected.maybe_patch import patch_maybe


class TestMaybePatch:
    """Test the maybe_patch module functionality."""

    def setup_method(self):
        """Apply the patch before each test."""
        patch_maybe()

    def test_patch_maybe_function(self):
        """Test that patch_maybe function exists and is callable."""
        assert callable(patch_maybe)

    def test_maybe_or_with_some_left(self):
        """Test __or__ operator with Some on left side."""
        some_value = Some(42)
        other_value = Some(99)

        result = some_value | other_value

        # Should return the left side (Some(42))
        assert result == some_value
        assert result.unwrap() == 42

    def test_maybe_or_with_nothing_left(self):
        """Test __or__ operator with Nothing on left side."""
        nothing_value = Nothing
        some_value = Some(42)

        result = nothing_value | some_value

        # Should return the right side (Some(42))
        assert result == some_value
        assert result.unwrap() == 42

    def test_maybe_or_both_nothing(self):
        """Test __or__ operator with both Nothing."""
        result = Nothing | Nothing

        # Should return Nothing
        assert result is Nothing

    def test_maybe_or_chaining(self):
        """Test chaining __or__ operations."""
        result = Nothing | Nothing | Some(42) | Some(99)

        # Should return the first Some value
        assert result == Some(42)

    def test_maybe_filter_with_true_predicate(self):
        """Test filter method with predicate returning True."""
        some_value = Some(42)

        result = some_value.filter(lambda x: x > 40)

        # Should keep the value
        assert result == some_value
        assert result.unwrap() == 42

    def test_maybe_filter_with_false_predicate(self):
        """Test filter method with predicate returning False."""
        some_value = Some(42)

        result = some_value.filter(lambda x: x > 50)

        # Should return Nothing
        assert result is ExprNothing

    def test_maybe_filter_on_nothing(self):
        """Test filter method on Nothing."""
        result = Nothing.filter(lambda x: True)

        # Should remain Nothing
        assert result is ExprNothing

    def test_maybe_filter_with_exception(self):
        """Test filter method when predicate raises exception."""
        some_value = Some(42)

        def failing_predicate(x):
            raise ValueError("Test error")

        # The filter should raise the exception, not return Nothing
        with pytest.raises(ValueError, match="Test error"):
            some_value.filter(failing_predicate)

    def test_maybe_has_patched_methods(self):
        """Test that Maybe class has the patched methods."""
        assert hasattr(Maybe, "__or__")
        assert hasattr(Maybe, "filter")

    def test_patch_idempotent(self):
        """Test that patch_maybe can be called multiple times."""
        # First patch was in setup_method
        patch_maybe()  # Second patch
        patch_maybe()  # Third patch

        # Should still work
        result = Some(42) | Some(99)
        assert result.unwrap() == 42


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
