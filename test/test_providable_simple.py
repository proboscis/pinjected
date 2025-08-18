"""Simple tests for providable.py module."""

import pytest
from typing import Union, get_args

from pinjected.providable import Providable, T
from pinjected.di.injected import Injected
from pinjected.di.proxiable import DelegatedVar


class TestProvidable:
    """Test the Providable type definition."""

    def test_providable_type_definition(self):
        """Test that Providable is a Union type."""
        # Check that Providable is a Union
        assert hasattr(Providable, "__origin__")
        assert Providable.__origin__ is Union

    def test_providable_includes_str(self):
        """Test that str is a valid Providable."""
        # This should not raise type errors
        value: Providable = "test_string"
        assert isinstance(value, str)

    def test_providable_includes_type(self):
        """Test that type[T] is a valid Providable."""

        class MyClass:
            pass

        value: Providable = MyClass
        assert value is MyClass

    def test_providable_includes_injected(self):
        """Test that Injected[T] is a valid Providable."""
        from pinjected.di.injected import InjectedPure

        injected = InjectedPure(42)
        value: Providable = injected
        assert isinstance(value, Injected)

    def test_providable_includes_callable(self):
        """Test that Callable is a valid Providable."""

        def my_function():
            return 42

        value: Providable = my_function
        assert callable(value)

    def test_providable_includes_delegatedvar(self):
        """Test that DelegatedVar is a valid Providable."""
        # Create a mock DelegatedVar
        from unittest.mock import Mock

        mock_delegated = Mock(spec=DelegatedVar)

        value: Providable = mock_delegated
        assert value is mock_delegated

    def test_type_var_t(self):
        """Test that T is a TypeVar."""
        from typing import TypeVar as TV

        assert isinstance(T, TV)
        assert T.__name__ == "T"

    def test_providable_type_args(self):
        """Test the arguments of Providable Union."""
        args = get_args(Providable)

        # Should have 5 types in the Union
        assert len(args) == 5

        # Check that str is in the args
        assert str in args

    def test_module_imports(self):
        """Test that the module imports correctly."""
        import pinjected.providable as module

        # Check imports
        assert hasattr(module, "Callable")
        assert hasattr(module, "TypeVar")
        assert hasattr(module, "Union")
        assert hasattr(module, "Injected")
        assert hasattr(module, "DelegatedVar")

        # Check exports
        assert hasattr(module, "T")
        assert hasattr(module, "Providable")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
