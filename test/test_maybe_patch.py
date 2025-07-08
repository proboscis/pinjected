"""Tests for maybe_patch.py module."""

import pytest
from returns.maybe import Maybe, Some, Nothing as ReturnsNothing
from expression import Nothing as ExpressionNothing

from pinjected.maybe_patch import patch_maybe


class TestMaybePatch:
    """Tests for the maybe_patch functionality."""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Setup and teardown for each test."""
        # Store original methods if they exist
        original_or = getattr(Maybe, "__or__", None)
        original_filter = getattr(Maybe, "filter", None)

        # Apply the patch
        patch_maybe()

        yield

        # Restore original methods
        if original_or is None:
            delattr(Maybe, "__or__")
        else:
            Maybe.__or__ = original_or

        if original_filter is None:
            delattr(Maybe, "filter")
        else:
            Maybe.filter = original_filter

    def test_patch_adds_or_method(self):
        """Test that patch_maybe adds __or__ method to Maybe."""
        assert hasattr(Maybe, "__or__")
        assert callable(getattr(Maybe, "__or__"))

    def test_patch_adds_filter_method(self):
        """Test that patch_maybe adds filter method to Maybe."""
        assert hasattr(Maybe, "filter")
        assert callable(getattr(Maybe, "filter"))

    def test_or_with_some_returns_self(self):
        """Test that Some | other returns Some."""
        some_value = Some(42)
        other_value = Some(100)

        result = some_value | other_value

        assert result == some_value
        assert result.unwrap() == 42

    def test_or_with_nothing_returns_other(self):
        """Test that Nothing | other returns other."""
        nothing = ReturnsNothing
        some_value = Some(42)

        result = nothing | some_value

        assert result == some_value
        assert result.unwrap() == 42

    def test_or_nothing_with_nothing(self):
        """Test that Nothing | Nothing returns Nothing."""
        nothing1 = ReturnsNothing
        nothing2 = ReturnsNothing

        result = nothing1 | nothing2

        assert result == nothing2

    def test_or_chain_operations(self):
        """Test chaining or operations."""
        nothing = ReturnsNothing
        some1 = Some(1)
        some2 = Some(2)

        # Nothing | Some(1) | Some(2) should return Some(1)
        result = nothing | some1 | some2
        assert result == some1

        # Some(1) | Nothing | Some(2) should return Some(1)
        result2 = some1 | nothing | some2
        assert result2 == some1

    def test_filter_with_true_predicate(self):
        """Test filter keeps value when predicate returns True."""
        some_value = Some(42)

        result = some_value.filter(lambda x: x > 40)

        assert result == some_value
        assert result.unwrap() == 42

    def test_filter_with_false_predicate(self):
        """Test filter returns Nothing when predicate returns False."""
        some_value = Some(42)

        result = some_value.filter(lambda x: x < 40)

        # The function returns expression.Nothing, not returns.Nothing
        assert result == ExpressionNothing

    def test_filter_on_nothing(self):
        """Test filter on Nothing returns Nothing."""
        nothing = ReturnsNothing

        result = nothing.filter(lambda x: True)

        assert result == ExpressionNothing

    def test_filter_with_exception_in_predicate(self):
        """Test filter handles exceptions in predicate."""
        some_value = Some(42)

        def failing_predicate(x):
            raise ValueError("Test error")

        # When the predicate raises an exception, it will propagate
        # This is the actual behavior of returns.maybe.map
        with pytest.raises(ValueError, match="Test error"):
            some_value.filter(failing_predicate)

    def test_filter_with_complex_predicate(self):
        """Test filter with complex predicates."""
        some_dict = Some({"name": "test", "value": 42})

        # Test accessing nested values
        result = some_dict.filter(lambda d: d["value"] > 40)
        assert result == some_dict

        result2 = some_dict.filter(lambda d: d["value"] < 40)
        assert result2 == ExpressionNothing

    def test_multiple_patch_calls(self):
        """Test that calling patch_maybe multiple times doesn't break."""
        # First patch already applied in setup

        # Apply patch again
        patch_maybe()

        # Should still work
        some_value = Some(10)
        result = some_value | Some(20)
        assert result == some_value

        result2 = some_value.filter(lambda x: x == 10)
        assert result2 == some_value


def test_patch_maybe_integration():
    """Integration test showing practical usage."""
    # Apply the patch
    patch_maybe()

    # Create a chain of Maybe operations
    def get_user_age(user_id):
        if user_id == 1:
            return Some({"name": "Alice", "age": 25})
        return ReturnsNothing

    # Use the patched or operator
    user = get_user_age(2) | get_user_age(1) | Some({"name": "Default", "age": 0})

    assert user.unwrap()["name"] == "Alice"
    assert user.unwrap()["age"] == 25

    # Use the patched filter method
    adult_user = user.filter(lambda u: u["age"] >= 18)
    assert adult_user == user

    minor_user = user.filter(lambda u: u["age"] < 18)
    assert minor_user == ExpressionNothing


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
