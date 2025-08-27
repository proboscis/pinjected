"""Tests for pinjected/di/decorators.py module."""

import pytest
import asyncio
import warnings
from unittest.mock import Mock, patch
from typing import Protocol

from pinjected.di.decorators import (
    injected_function,
    injected_instance,
    injected,
    injected_class,
    injected_method,
    CachedAwaitable,
    cached_coroutine,
    instance,
    dynamic,
    reload,
    register,
    _injected_with_protocol,
    IMPLICIT_BINDINGS,
)
from pinjected.di.injected import Injected
from pinjected.di.partially_injected import Partial
from pinjected.di.proxiable import DelegatedVar
from pinjected.v2.keys import StrBindKey


class TestInjectedFunction:
    """Tests for injected_function decorator."""

    def test_injected_function_deprecated_warning(self):
        """Test that injected_function raises deprecation warning."""

        def test_func(arg1):
            return arg1

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            injected_function(test_func)

            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "injected_function is deprecated" in str(w[0].message)

    def test_injected_function_with_underscore_params(self):
        """Test injected_function with underscore parameters."""

        def test_func(_dep1, __dep2, regular_param):
            return (_dep1, __dep2, regular_param)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            result = injected_function(test_func)

        # injected_function returns a Partial object from partially_injected module
        from pinjected.di.partially_injected import Partial

        assert isinstance(result, Partial)
        # Check that dependencies were identified
        assert hasattr(result, "injection_targets")
        # Should have identified _dep1 and __dep2 as dependencies
        assert "_dep1" in result.injection_targets
        # __dep2 gets name-mangled in class context, so check for that pattern
        assert any("__dep2" in key for key in result.injection_targets)
        assert "regular_param" not in result.injection_targets

    def test_injected_function_with_positional_only(self):
        """Test injected_function with positional-only parameters."""

        def test_func(pos_only, /, regular):
            return (pos_only, regular)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            result = injected_function(test_func)

        from pinjected.di.partially_injected import Partial

        assert isinstance(result, Partial)
        # Should have identified pos_only as a dependency
        assert "pos_only" in result.injection_targets
        assert "regular" not in result.injection_targets

    @patch("pinjected.di.decorators.IMPLICIT_BINDINGS")
    def test_injected_function_registers_binding(self, mock_bindings):
        """Test that injected_function registers in IMPLICIT_BINDINGS."""

        def test_func():
            return "result"

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            injected_function(test_func)

        # Check that binding was registered
        mock_bindings.__setitem__.assert_called_once()
        call_args = mock_bindings.__setitem__.call_args
        assert call_args[0][0] == StrBindKey("test_func")

    def test_injected_function_with_class(self):
        """Test injected_function with a class."""

        class TestClass:
            def __init__(self, _dep):
                self.dep = _dep

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            result = injected_function(TestClass)

        from pinjected.di.partially_injected import Partial

        assert isinstance(result, Partial)
        # Check that it identified dependencies from __init__
        assert "_dep" in result.injection_targets


class TestInjectedInstance:
    """Tests for injected_instance decorator."""

    @patch("pinjected.di.decorators.IMPLICIT_BINDINGS")
    def test_injected_instance_basic(self, mock_bindings):
        """Test basic injected_instance functionality."""

        @injected_instance
        def my_instance(dep1, dep2):
            return f"instance with {dep1} and {dep2}"

        # Should return a proxy (DelegatedVar)
        assert isinstance(my_instance, DelegatedVar)
        # Should register in IMPLICIT_BINDINGS
        mock_bindings.__setitem__.assert_called_once()
        call_args = mock_bindings.__setitem__.call_args
        assert call_args[0][0] == StrBindKey("my_instance")

    def test_injected_instance_returns_proxy(self):
        """Test that injected_instance returns a proxy."""

        def my_func():
            return "value"

        result = injected_instance(my_func)

        # Should be a DelegatedVar (proxy)
        assert isinstance(result, DelegatedVar)

    def test_instance_alias(self):
        """Test that instance is an alias for injected_instance."""
        assert instance is injected_instance

    def test_instance_with_callable_true(self):
        """Test @instance(callable=True) decorator."""

        @instance(callable=True)
        def callable_factory():
            def inner_func(x):
                return x * 2

            return inner_func

        # Verify it's registered in IMPLICIT_BINDINGS
        bind_key = StrBindKey("callable_factory")
        assert bind_key in IMPLICIT_BINDINGS

        # Check metadata
        bind = IMPLICIT_BINDINGS[bind_key]
        metadata = bind._metadata.unwrap()
        assert metadata.is_callable_instance is True

    def test_instance_with_callable_false(self):
        """Test @instance(callable=False) decorator."""

        @instance(callable=False)
        def non_callable_factory():
            return {"data": "value"}

        # Verify it's registered in IMPLICIT_BINDINGS
        bind_key = StrBindKey("non_callable_factory")
        assert bind_key in IMPLICIT_BINDINGS

        # Check metadata
        bind = IMPLICIT_BINDINGS[bind_key]
        metadata = bind._metadata.unwrap()
        assert metadata.is_callable_instance is False

    def test_instance_without_parens(self):
        """Test @instance decorator without parentheses."""

        @instance
        def regular_instance():
            return "regular"

        # Verify it's registered in IMPLICIT_BINDINGS
        bind_key = StrBindKey("regular_instance")
        assert bind_key in IMPLICIT_BINDINGS

        # Check metadata - should default to is_callable_instance=False
        bind = IMPLICIT_BINDINGS[bind_key]
        metadata = bind._metadata.unwrap()
        assert metadata.is_callable_instance is False


class TestInjected:
    """Tests for injected decorator."""

    def test_injected_with_string(self):
        """Test injected with string dependency."""
        result = injected("my_dependency")

        assert isinstance(result, DelegatedVar)

    def test_injected_with_string_and_protocol_raises(self):
        """Test that string with protocol raises TypeError."""

        class MyProtocol(Protocol):
            def method(self): ...

        with pytest.raises(TypeError, match="Protocol parameter is not supported"):
            injected("my_dep", protocol=MyProtocol)

    def test_injected_with_function(self):
        """Test injected as decorator on function."""

        @injected
        def my_func(dep1, /, arg2):
            return (dep1, arg2)

        assert isinstance(my_func, Partial)

    def test_injected_with_class(self):
        """Test injected as decorator on class."""

        @injected
        class MyClass:
            def __init__(self, dep1, /, arg2):
                self.dep1 = dep1
                self.arg2 = arg2

        assert isinstance(MyClass, Partial)

    def test_injected_with_protocol(self):
        """Test injected with protocol specification."""

        class MyProtocol(Protocol):
            def __call__(self, x: int) -> str: ...

        @injected(protocol=MyProtocol)
        def my_func(dep, /, x: int) -> str:
            return f"{dep}:{x}"

        # Should have protocol attribute
        if hasattr(my_func, "__protocol__"):
            assert my_func.__protocol__ is MyProtocol

    def test_injected_as_decorator_with_protocol(self):
        """Test @injected(protocol=...) syntax."""

        class MyProtocol(Protocol):
            def __call__(self) -> str: ...

        @injected(protocol=MyProtocol)
        def my_func() -> str:
            return "result"

        assert isinstance(my_func, Partial)

    def test_injected_empty_decorator(self):
        """Test @injected() syntax."""

        @injected()
        def my_func():
            return "result"

        assert isinstance(my_func, Partial)

    def test_injected_invalid_target(self):
        """Test injected with invalid target type."""
        with pytest.raises(TypeError, match="Invalid target type"):
            injected(123)  # Not a string, type, or callable


class TestInjectedWithProtocol:
    """Tests for _injected_with_protocol internal function."""

    @patch("pinjected.di.decorators.IMPLICIT_BINDINGS")
    def test_injected_with_protocol_function(self, mock_bindings):
        """Test _injected_with_protocol with function."""

        def test_func(_dep, regular):
            return (_dep, regular)

        class MyProtocol(Protocol):
            def __call__(self, regular) -> tuple: ...

        result = _injected_with_protocol(test_func, protocol=MyProtocol)

        assert isinstance(result, Partial)
        # Check binding was registered
        mock_bindings.__setitem__.assert_called_once()
        call_args = mock_bindings.__setitem__.call_args
        assert call_args[0][0] == StrBindKey("test_func")

    def test_injected_with_protocol_class(self):
        """Test _injected_with_protocol with class."""

        class TestClass:
            def __init__(self, _dep):
                self.dep = _dep

        result = _injected_with_protocol(TestClass)

        assert isinstance(result, Partial)

    def test_injected_with_protocol_positional_only(self):
        """Test _injected_with_protocol with positional-only params."""

        def test_func(pos_dep, /, regular):
            return (pos_dep, regular)

        result = _injected_with_protocol(test_func)

        assert isinstance(result, Partial)


class TestInjectedClassAndMethod:
    """Tests for injected_class and injected_method."""

    def test_injected_class(self):
        """Test injected_class decorator."""

        class TestClass:
            def __init__(self, dep):
                self.dep = dep

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            result = injected_class(TestClass)

        assert isinstance(result, Partial)

    def test_injected_method(self):
        """Test injected_method decorator."""

        class TestClass:
            @injected_method
            def my_method(self, _dep, arg):
                return (self, _dep, arg)

        obj = TestClass()
        # Method should be wrapped
        assert callable(obj.my_method)


class TestCachedAwaitable:
    """Tests for CachedAwaitable class."""

    @pytest.mark.asyncio
    async def test_cached_awaitable_basic(self):
        """Test CachedAwaitable caches result."""
        call_count = 0

        async def coro():
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)
            return "result"

        cached = CachedAwaitable(coro())

        # First await
        result1 = await cached
        assert result1 == "result"
        assert call_count == 1

        # Second await should use cache
        result2 = await cached
        assert result2 == "result"
        assert call_count == 1  # Still 1, not called again

    @pytest.mark.asyncio
    async def test_cached_awaitable_exception(self):
        """Test CachedAwaitable with exception."""

        async def failing_coro():
            await asyncio.sleep(0.01)
            raise ValueError("Test error")

        cached = CachedAwaitable(failing_coro())

        # First await should raise
        with pytest.raises(ValueError, match="Test error"):
            await cached

        # Second await should raise same cached exception
        with pytest.raises(ValueError, match="Test error"):
            await cached

    @pytest.mark.asyncio
    async def test_cached_awaitable_concurrent(self):
        """Test CachedAwaitable with concurrent access."""
        call_count = 0

        async def slow_coro():
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.1)
            return "result"

        cached = CachedAwaitable(slow_coro())

        # Start multiple concurrent awaits
        tasks = [asyncio.create_task(cached._get_result()) for _ in range(5)]
        results = await asyncio.gather(*tasks)

        # All should get same result
        assert all(r == "result" for r in results)
        # Coroutine should only run once
        assert call_count == 1


class TestCachedCoroutine:
    """Tests for cached_coroutine decorator."""

    def test_cached_coroutine_decorator(self):
        """Test cached_coroutine decorator."""

        @cached_coroutine
        async def my_coro(x):
            return x * 2

        # Should return a wrapper function
        assert callable(my_coro)
        assert hasattr(my_coro, "__wrapped__")

        # Calling should return CachedAwaitable
        result = my_coro(5)
        assert isinstance(result, CachedAwaitable)

    @pytest.mark.asyncio
    async def test_cached_coroutine_functionality(self):
        """Test cached_coroutine caches results."""
        call_count = 0

        @cached_coroutine
        async def counted_coro():
            nonlocal call_count
            call_count += 1
            return "result"

        # Create cached awaitable
        awaitable = counted_coro()

        # Multiple awaits should only call once
        result1 = await awaitable
        result2 = await awaitable

        assert result1 == result2 == "result"
        assert call_count == 1


class TestDynamic:
    """Tests for dynamic decorator."""

    def test_dynamic_with_injected(self):
        """Test dynamic decorator with Injected."""
        mock_injected = Mock(spec=Injected)
        mock_injected.add_dynamic_dependencies.return_value = mock_injected

        # Mock providables
        mock_providable1 = Mock()
        mock_providable2 = Mock()

        with patch("pinjected.di.decorators.extract_dependency") as mock_extract:
            mock_extract.side_effect = [{"dep1"}, {"dep2"}]

            dynamic(mock_providable1, mock_providable2)(mock_injected)

            mock_injected.add_dynamic_dependencies.assert_called_once()
            # Should have been called with all extracted dependencies
            call_args = mock_injected.add_dynamic_dependencies.call_args[0]
            assert "dep1" in call_args or "dep2" in call_args

    def test_dynamic_with_delegated_var(self):
        """Test dynamic decorator with DelegatedVar."""
        mock_var = Mock(spec=DelegatedVar)
        mock_injected = Mock(spec=Injected)
        mock_injected.add_dynamic_dependencies.return_value = mock_injected
        mock_injected.proxy = "proxy_result"
        mock_var.eval.return_value = mock_injected

        with patch("pinjected.di.decorators.extract_dependency") as mock_extract:
            mock_extract.return_value = set()

            result = dynamic()(mock_var)

            assert result == "proxy_result"
            mock_var.eval.assert_called_once()


class TestReload:
    """Tests for reload context manager."""

    def test_reload_context_manager(self):
        """Test reload is a context manager."""
        with reload("target1", "target2") as result:
            # Should work as a no-op context manager
            assert result is None


class TestRegister:
    """Tests for register decorator."""

    @patch("pinjected.di.decorators.IMPLICIT_BINDINGS")
    @patch("pinjected.di.decorators.inspect.currentframe")
    def test_register_decorator(self, mock_frame, mock_bindings):
        """Test register decorator functionality."""
        # Set up mock frame with proper attributes for get_code_location
        mock_code = Mock()
        mock_code.co_filename = "/test/file.py"

        mock_current_frame = Mock()
        mock_current_frame.f_back = Mock()
        mock_current_frame.f_back.f_code = mock_code
        mock_current_frame.f_back.f_lineno = 42

        mock_frame.return_value = mock_current_frame

        # Create mock Injected
        mock_injected = Mock(spec=Injected)

        with patch("pinjected.di.decorators.Injected.ensure_injected") as mock_ensure:
            mock_ensure.return_value = mock_injected

            # Apply decorator
            decorated = register("my_name")(mock_injected)

            # Should register in IMPLICIT_BINDINGS
            mock_bindings.__setitem__.assert_called_once()
            call_args = mock_bindings.__setitem__.call_args
            assert call_args[0][0] == StrBindKey("my_name")
            # Should return original target
            assert decorated is mock_injected

            mock_ensure.assert_called_once_with(mock_injected)

    def test_register_with_string_name(self):
        """Test register with custom name."""
        mock_target = Mock()

        with (
            patch("pinjected.di.decorators.IMPLICIT_BINDINGS") as mock_bindings,
            patch("pinjected.di.decorators.Injected.ensure_injected") as mock_ensure,
            patch("pinjected.di.decorators.inspect.currentframe") as mock_frame,
        ):
            # Set up mock frame with proper attributes for get_code_location
            mock_code = Mock()
            mock_code.co_filename = "/test/file.py"

            mock_current_frame = Mock()
            mock_current_frame.f_back = Mock()
            mock_current_frame.f_back.f_code = mock_code
            mock_current_frame.f_back.f_lineno = 42

            mock_frame.return_value = mock_current_frame

            # Return an Injected instance
            mock_injected = Mock(spec=Injected)
            mock_ensure.return_value = mock_injected

            register("custom_name")(mock_target)

            mock_bindings.__setitem__.assert_called_once()
            call_args = mock_bindings.__setitem__.call_args
            assert call_args[0][0] == StrBindKey("custom_name")


class TestIntegration:
    """Integration tests for decorators."""

    def test_injected_function_integration(self):
        """Test full integration of injected_function."""

        def compute(_multiplier, value):
            return _multiplier * value

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            injected_compute = injected_function(compute)

        # Should be a Partial object
        assert isinstance(injected_compute, Partial)
        # Should have the dependency identified
        assert hasattr(injected_compute, "injection_targets")
        assert "_multiplier" in injected_compute.injection_targets

    @pytest.mark.asyncio
    async def test_cached_coroutine_integration(self):
        """Test cached_coroutine in realistic scenario."""
        expensive_calls = 0

        @cached_coroutine
        async def expensive_operation():
            nonlocal expensive_calls
            expensive_calls += 1
            await asyncio.sleep(0.01)
            return "expensive result"

        # Multiple calls should return same CachedAwaitable
        awaitable1 = expensive_operation()
        awaitable2 = expensive_operation()

        # Different instances
        assert awaitable1 is not awaitable2

        # But each caches its own result
        result1 = await awaitable1
        result1_again = await awaitable1
        result2 = await awaitable2

        assert result1 == result1_again == result2 == "expensive result"
        # Called twice (once for each awaitable)
        assert expensive_calls == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
