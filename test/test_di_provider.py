"""Tests for pinjected.di.provider module."""

import pytest
from unittest.mock import Mock
from pinjected.di.provider import Provider


class TestProvider:
    """Test Provider class."""

    def test_provider_initialization(self):
        """Test Provider can be initialized with dependencies and function."""

        def test_func(a, b):
            return a + b

        provider = Provider(dependencies=["dep1", "dep2"], function=test_func)

        assert provider.dependencies == ["dep1", "dep2"]
        assert provider.function is test_func

    def test_provider_empty_dependencies(self):
        """Test Provider with empty dependencies list."""

        def no_deps_func():
            return "no dependencies"

        provider = Provider(dependencies=[], function=no_deps_func)

        assert provider.dependencies == []
        assert provider.function is no_deps_func

    def test_get_provider_function_simple(self):
        """Test get_provider_function creates function with correct signature."""

        def impl(x, y):
            return x + y

        provider = Provider(dependencies=["x", "y"], function=impl)
        provider_func = provider.get_provider_function()

        # Test the created function
        result = provider_func(10, 20)
        assert result == 30

        # Check function name
        assert provider_func.__name__ == "provider_function"

    def test_get_provider_function_no_dependencies(self):
        """Test get_provider_function with no dependencies."""

        def impl():
            return 42

        provider = Provider(dependencies=[], function=impl)
        provider_func = provider.get_provider_function()

        # Test the created function
        result = provider_func()
        assert result == 42

    def test_get_provider_function_single_dependency(self):
        """Test get_provider_function with single dependency."""

        def impl(value):
            return value * 2

        provider = Provider(dependencies=["value"], function=impl)
        provider_func = provider.get_provider_function()

        # Test the created function
        result = provider_func(21)
        assert result == 42

    def test_get_provider_function_with_kwargs(self):
        """Test get_provider_function handles keyword arguments."""

        def impl(a, b, c=10):
            return a + b + c

        provider = Provider(dependencies=["a", "b"], function=impl)
        provider_func = provider.get_provider_function()

        # Test with positional args
        result = provider_func(1, 2)
        assert result == 13  # 1 + 2 + 10 (default)

    def test_provider_function_preserves_closure(self):
        """Test that provider function preserves closures."""
        multiplier = 5

        def impl(x):
            return x * multiplier

        provider = Provider(dependencies=["x"], function=impl)
        provider_func = provider.get_provider_function()

        result = provider_func(10)
        assert result == 50

    def test_provider_with_mock_function(self):
        """Test Provider with mock function."""
        mock_func = Mock(return_value="mocked result")

        provider = Provider(dependencies=["arg1", "arg2"], function=mock_func)
        provider_func = provider.get_provider_function()

        # makefun creates functions with keyword arguments
        result = provider_func(arg1="a", arg2="b")
        assert result == "mocked result"
        mock_func.assert_called_once_with(arg1="a", arg2="b")

    def test_provider_dataclass_fields(self):
        """Test Provider is a proper dataclass."""

        def func():
            pass

        provider = Provider(dependencies=["x"], function=func)

        # Test dataclass features
        assert hasattr(provider, "__dataclass_fields__")
        assert "dependencies" in provider.__dataclass_fields__
        assert "function" in provider.__dataclass_fields__

    def test_provider_function_with_varargs(self):
        """Test provider function with variable arguments."""

        def impl(*args):
            return sum(args)

        provider = Provider(dependencies=[], function=impl)
        provider_func = provider.get_provider_function()

        # makefun might handle this differently
        result = provider_func()
        assert result == 0  # sum of empty args

    def test_provider_repr(self):
        """Test Provider string representation."""

        def test_func():
            pass

        provider = Provider(dependencies=["a", "b"], function=test_func)
        repr_str = repr(provider)

        # Should contain class name and fields
        assert "Provider" in repr_str
        assert "dependencies" in repr_str
        assert "['a', 'b']" in repr_str

    def test_multiple_providers_independent(self):
        """Test multiple Provider instances are independent."""

        def func1(x):
            return x * 2

        def func2(y):
            return y + 10

        provider1 = Provider(dependencies=["x"], function=func1)
        provider2 = Provider(dependencies=["y"], function=func2)

        pf1 = provider1.get_provider_function()
        pf2 = provider2.get_provider_function()

        assert pf1(5) == 10
        assert pf2(5) == 15

        # Ensure they have different signatures
        assert pf1.__name__ == pf2.__name__  # Both named "provider_function"
        # But they should work independently
        assert pf1(3) == 6
        assert pf2(3) == 13


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
