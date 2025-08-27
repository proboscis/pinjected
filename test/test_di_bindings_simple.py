"""Simple tests for di/bindings.py module."""

import pytest
from typing import TypeVar

from pinjected.di.bindings import T, U


class TestTypeVariables:
    """Test the type variables defined in bindings module."""

    def test_t_type_variable_exists(self):
        """Test that T type variable exists."""
        assert T is not None
        assert isinstance(T, TypeVar)

    def test_u_type_variable_exists(self):
        """Test that U type variable exists."""
        assert U is not None
        assert isinstance(U, TypeVar)

    def test_type_variable_names(self):
        """Test that type variables have correct names."""
        assert T.__name__ == "T"
        assert U.__name__ == "U"

    def test_type_variables_are_distinct(self):
        """Test that T and U are distinct type variables."""
        assert T is not U
        assert id(T) != id(U)

    def test_can_import_from_module(self):
        """Test that we can import from the module."""
        from pinjected.di import bindings

        assert hasattr(bindings, "T")
        assert hasattr(bindings, "U")
        assert bindings.T is T
        assert bindings.U is U

    def test_type_variables_in_generic_class(self):
        """Test using the type variables in a generic class."""
        from typing import Generic

        class Container(Generic[T]):
            def __init__(self, value: T):
                self.value = value

        class Mapper(Generic[T, U]):
            def map(self, value: T) -> U:
                pass

        # Should be able to use with the type variables
        container_int = Container[int](5)
        assert container_int.value == 5

        mapper = Mapper[str, int]()
        assert mapper is not None

    def test_type_variable_constraints(self):
        """Test that type variables have no constraints."""
        # T and U should be unconstrained TypeVars
        assert T.__constraints__ == ()
        assert U.__constraints__ == ()

        # Should not have bounds
        assert T.__bound__ is None
        assert U.__bound__ is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
