"""Tests for pinjected.di.bindings module."""

import pytest
from typing import TypeVar
from pinjected.di.bindings import T, U


class TestTypeVariables:
    """Test type variables defined in bindings module."""

    def test_T_is_typevar(self):
        """Test that T is a TypeVar."""
        assert isinstance(T, TypeVar)

    def test_U_is_typevar(self):
        """Test that U is a TypeVar."""
        assert isinstance(U, TypeVar)

    def test_T_name(self):
        """Test T has correct name."""
        assert T.__name__ == "T"

    def test_U_name(self):
        """Test U has correct name."""
        assert U.__name__ == "U"

    def test_type_variables_are_distinct(self):
        """Test T and U are distinct type variables."""
        assert T is not U
        assert T != U

    def test_type_variables_in_generic_class(self):
        """Test type variables can be used in generic classes."""
        from typing import Generic

        class Container(Generic[T]):
            def __init__(self, value: T):
                self.value = value

        class Transformer(Generic[T, U]):
            def transform(self, value: T) -> U:
                pass

        # Should not raise any errors
        container = Container(42)
        assert container.value == 42

        transformer = Transformer()
        assert hasattr(transformer, "transform")

    def test_type_variables_in_function_annotations(self):
        """Test type variables can be used in function annotations."""

        def identity(value: T) -> T:
            return value

        def transform(value: T, func) -> U:
            return func(value)

        # Test functions work
        assert identity(42) == 42
        assert identity("hello") == "hello"
        assert transform(5, str) == "5"

    def test_type_variables_no_constraints(self):
        """Test that T and U have no constraints."""
        # TypeVars without constraints accept any type
        assert T.__constraints__ == ()
        assert U.__constraints__ == ()

    def test_type_variables_no_bound(self):
        """Test that T and U have no bound."""
        assert T.__bound__ is None
        assert U.__bound__ is None

    def test_type_variables_not_covariant_or_contravariant(self):
        """Test variance properties of type variables."""
        # By default, TypeVars are invariant
        assert not T.__covariant__
        assert not T.__contravariant__
        assert not U.__covariant__
        assert not U.__contravariant__

    def test_module_exports(self):
        """Test that module exports T and U."""
        from pinjected.di import bindings

        assert hasattr(bindings, "T")
        assert hasattr(bindings, "U")
        assert bindings.T is T
        assert bindings.U is U

    def test_type_variable_repr(self):
        """Test string representation of type variables."""
        assert repr(T) == "~T"
        assert repr(U) == "~U"

    def test_can_import_individually(self):
        """Test individual imports work."""
        from pinjected.di.bindings import T as T_imported
        from pinjected.di.bindings import U as U_imported

        assert T_imported is T
        assert U_imported is U


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
