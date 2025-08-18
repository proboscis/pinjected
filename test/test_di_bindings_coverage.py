"""Simple tests for di/bindings.py module."""

import pytest
from typing import TypeVar

from pinjected.di.bindings import T, U


class TestBindingsTypeVars:
    """Test the TypeVar definitions in bindings module."""

    def test_T_is_typevar(self):
        """Test that T is a TypeVar."""
        assert isinstance(T, TypeVar)
        assert T.__name__ == "T"

    def test_U_is_typevar(self):
        """Test that U is a TypeVar."""
        assert isinstance(U, TypeVar)
        assert U.__name__ == "U"

    def test_typevars_are_distinct(self):
        """Test that T and U are distinct TypeVars."""
        assert T is not U
        assert T.__name__ != U.__name__

    def test_can_use_typevars_in_annotations(self):
        """Test that TypeVars can be used in type annotations."""

        def identity(x: T) -> T:
            return x

        def swap(x: T, y: U) -> tuple[U, T]:
            return y, x

        # Test the functions work
        assert identity(5) == 5
        assert identity("hello") == "hello"
        assert swap(1, "a") == ("a", 1)

    def test_typevars_in_generic_class(self):
        """Test TypeVars can be used in generic classes."""
        from typing import Generic

        class Container(Generic[T]):
            def __init__(self, value: T):
                self.value = value

            def get(self) -> T:
                return self.value

        class Pair(Generic[T, U]):
            def __init__(self, first: T, second: U):
                self.first = first
                self.second = second

        # Test instantiation
        c1 = Container(42)
        assert c1.get() == 42

        c2 = Container("test")
        assert c2.get() == "test"

        p = Pair(1, "one")
        assert p.first == 1
        assert p.second == "one"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
