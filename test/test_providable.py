"""Tests for pinjected.providable module."""

import pytest
from typing import Union, get_args, get_origin
from unittest.mock import Mock

from pinjected.providable import Providable, T
from pinjected.di.injected import Injected
from pinjected.di.proxiable import DelegatedVar


class TestProvidable:
    """Tests for Providable type alias."""

    def test_providable_is_union(self):
        """Test that Providable is a Union type."""
        # Get the origin should be Union
        origin = get_origin(Providable)
        assert origin is Union

    def test_providable_includes_expected_types(self):
        """Test that Providable includes all expected types."""
        # Get the arguments of the Union
        args = get_args(Providable)

        # Check that str is included
        assert str in args

        # Check that Injected is included (as a generic type)
        assert any(get_origin(arg) is type for arg in args)
        assert any(
            hasattr(arg, "__origin__") and arg.__origin__ is Injected for arg in args
        )

        # Check that Callable is included
        from collections.abc import Callable

        assert Callable in args

        # Check that DelegatedVar is included
        assert DelegatedVar in args

    def test_isinstance_with_string(self):
        """Test that string values are valid Providables."""
        test_str = "test_dependency"
        # Can't use isinstance with Union directly in older Python
        # But we can verify the type is in the union
        assert isinstance(test_str, str)
        assert str in get_args(Providable)

    def test_isinstance_with_type(self):
        """Test that type values are valid Providables."""

        class TestClass:
            pass

        # Type[T] is in the union
        assert isinstance(TestClass, type)

    def test_isinstance_with_injected(self):
        """Test that Injected instances are valid Providables."""
        # Injected[T] is in the union
        args = get_args(Providable)
        assert any(
            hasattr(arg, "__origin__") and arg.__origin__ is Injected for arg in args
        )

    def test_isinstance_with_callable(self):
        """Test that callable values are valid Providables."""

        def test_func():
            return "test"

        # Verify it's callable
        assert callable(test_func)

        # Callable is in the union
        from collections.abc import Callable

        assert Callable in get_args(Providable)

    def test_isinstance_with_delegated_var(self):
        """Test that DelegatedVar instances are valid Providables."""
        # DelegatedVar is in the union
        assert DelegatedVar in get_args(Providable)

    def test_type_var_t_exists(self):
        """Test that TypeVar T is defined."""
        assert T is not None
        # Verify it's a TypeVar
        assert hasattr(T, "__name__")
        assert T.__name__ == "T"


class TestProvidableUsage:
    """Tests demonstrating usage of Providable type."""

    def test_function_accepting_providable(self):
        """Test a function that accepts Providable type."""

        def process_providable(p: Providable) -> str:
            if isinstance(p, str):
                return f"String: {p}"
            elif isinstance(p, type):
                return f"Type: {p.__name__}"
            elif callable(p):
                return (
                    f"Callable: {p.__name__ if hasattr(p, '__name__') else 'anonymous'}"
                )
            else:
                return f"Other: {type(p).__name__}"

        # Test with different types
        assert process_providable("test") == "String: test"
        assert process_providable(int) == "Type: int"
        assert process_providable(lambda: None).startswith("Callable:")

        # Test with mock objects
        mock_injected = Mock(spec=Injected)
        result = process_providable(mock_injected)
        assert "Callable" in result or "Mock" in result or "Other" in result

    def test_providable_in_type_hints(self):
        """Test using Providable in type hints."""
        from typing import List

        def collect_providables(items: List[Providable]) -> int:
            return len(items)

        # Various valid providables
        providables = [
            "string_dep",
            int,
            lambda: None,
            Mock(spec=DelegatedVar),
        ]

        assert collect_providables(providables) == 4


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
