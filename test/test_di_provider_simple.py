"""Simple tests for di/provider.py module."""

import pytest
from unittest.mock import Mock, patch

from pinjected.di.provider import Provider


class TestProvider:
    """Test the Provider dataclass functionality."""

    def test_provider_creation(self):
        """Test creating a Provider instance."""
        deps = ["dep1", "dep2"]

        def func(dep1, dep2):
            return dep1 + dep2

        provider = Provider(dependencies=deps, function=func)

        assert provider.dependencies == deps
        assert provider.function is func

    def test_provider_with_no_dependencies(self):
        """Test Provider with empty dependencies."""

        def func():
            return "no deps"

        provider = Provider(dependencies=[], function=func)

        assert provider.dependencies == []
        assert provider.function is func

    @patch("pinjected.di.provider.create_function")
    def test_get_provider_function(self, mock_create_function):
        """Test get_provider_function method."""
        deps = ["x", "y", "z"]

        def func(x, y, z):
            return x + y + z

        mock_result = Mock()
        mock_create_function.return_value = mock_result

        provider = Provider(dependencies=deps, function=func)
        result = provider.get_provider_function()

        # Check that create_function was called correctly
        expected_signature = "provider_function(x,y,z)"
        mock_create_function.assert_called_once_with(expected_signature, func)
        assert result is mock_result

    @patch("pinjected.di.provider.create_function")
    def test_get_provider_function_single_dep(self, mock_create_function):
        """Test get_provider_function with single dependency."""
        deps = ["single_dep"]

        def func(single_dep):
            return single_dep * 2

        provider = Provider(dependencies=deps, function=func)
        provider.get_provider_function()

        expected_signature = "provider_function(single_dep)"
        mock_create_function.assert_called_once_with(expected_signature, func)

    def test_provider_is_dataclass(self):
        """Test that Provider has dataclass features."""

        def identity_func(a):
            return a

        provider1 = Provider(dependencies=["a"], function=identity_func)

        # Test repr
        repr_str = repr(provider1)
        assert "Provider" in repr_str
        assert "dependencies" in repr_str
        assert "function" in repr_str

        # Note: Equality won't work as expected because lambda functions
        # are different objects even with same code


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
