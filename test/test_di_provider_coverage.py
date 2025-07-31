"""Simple tests for di/provider.py module."""

import pytest
from dataclasses import is_dataclass
from collections.abc import Callable
import inspect

from pinjected.di.provider import Provider


class TestProvider:
    """Test the Provider dataclass."""

    def test_provider_is_dataclass(self):
        """Test that Provider is a dataclass."""
        assert is_dataclass(Provider)

    def test_provider_creation_simple(self):
        """Test creating Provider instance with simple function."""

        def simple_func(a, b):
            return a + b

        provider = Provider(dependencies=["dep1", "dep2"], function=simple_func)

        assert provider is not None
        assert provider.dependencies == ["dep1", "dep2"]
        assert provider.function is simple_func

    def test_provider_creation_empty_dependencies(self):
        """Test creating Provider with no dependencies."""

        def no_deps_func():
            return "result"

        provider = Provider(dependencies=[], function=no_deps_func)

        assert provider.dependencies == []
        assert provider.function is no_deps_func

    def test_get_provider_function_simple(self):
        """Test get_provider_function with simple case."""

        def impl(x, y):
            return x * y

        provider = Provider(dependencies=["x", "y"], function=impl)

        provider_func = provider.get_provider_function()

        # Check it's callable
        assert callable(provider_func)

        # Check signature
        sig = inspect.signature(provider_func)
        assert list(sig.parameters.keys()) == ["x", "y"]

        # Test calling it
        result = provider_func(3, 4)
        assert result == 12

    def test_get_provider_function_single_dependency(self):
        """Test get_provider_function with single dependency."""

        def impl(service):
            return f"Using {service}"

        provider = Provider(dependencies=["service"], function=impl)

        provider_func = provider.get_provider_function()

        # Check signature
        sig = inspect.signature(provider_func)
        assert list(sig.parameters.keys()) == ["service"]

        # Test calling
        result = provider_func("database")
        assert result == "Using database"

    def test_get_provider_function_no_dependencies(self):
        """Test get_provider_function with no dependencies."""

        def impl():
            return 42

        provider = Provider(dependencies=[], function=impl)

        provider_func = provider.get_provider_function()

        # Check signature - should have no parameters
        sig = inspect.signature(provider_func)
        assert len(sig.parameters) == 0

        # Test calling
        result = provider_func()
        assert result == 42

    def test_get_provider_function_many_dependencies(self):
        """Test get_provider_function with many dependencies."""

        def impl(a, b, c, d, e):
            return sum([a, b, c, d, e])

        provider = Provider(dependencies=["a", "b", "c", "d", "e"], function=impl)

        provider_func = provider.get_provider_function()

        # Check signature
        sig = inspect.signature(provider_func)
        assert list(sig.parameters.keys()) == ["a", "b", "c", "d", "e"]

        # Test calling
        result = provider_func(1, 2, 3, 4, 5)
        assert result == 15

    def test_provider_function_is_callable(self):
        """Test that function must be callable."""

        def func(x):
            return x * 2

        provider = Provider(dependencies=["x"], function=func)

        assert isinstance(provider.function, Callable)

    def test_provider_with_complex_function(self):
        """Test provider with more complex function."""

        def complex_func(db, cache, logger):
            # Simulate using dependencies
            logger_msg = f"Accessing {db} with {cache}"
            return {"db": db, "cache": cache, "log": logger_msg}

        provider = Provider(
            dependencies=["db", "cache", "logger"], function=complex_func
        )

        provider_func = provider.get_provider_function()
        result = provider_func("postgres", "redis", "loguru")

        assert result == {
            "db": "postgres",
            "cache": "redis",
            "log": "Accessing postgres with redis",
        }

    def test_provider_equality(self):
        """Test Provider equality."""

        def func1(x):
            return x

        def func2(x):
            return x * 2

        provider1 = Provider(["x"], func1)
        provider2 = Provider(["x"], func1)
        provider3 = Provider(["x"], func2)
        provider4 = Provider(["y"], func1)

        # Same dependencies and function
        assert provider1 == provider2

        # Different function
        assert provider1 != provider3

        # Different dependencies
        assert provider1 != provider4

    def test_provider_repr(self):
        """Test Provider string representation."""

        def func(x):
            return x

        provider = Provider(["dep1", "dep2"], func)

        repr_str = repr(provider)
        assert "Provider" in repr_str
        assert "dependencies" in repr_str


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
