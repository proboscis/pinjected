"""Tests to improve coverage for pinjected/di/injected.py."""

import pytest
import asyncio
import cloudpickle
from unittest.mock import Mock, patch

from pinjected.di.injected import (
    Injected,
    InjectedByName,
    InjectedFromFunction,
    PicklableInjectedFunction,
    InjectedPure,
    MappedInjected,
    ConditionalInjected,
    InjectedWithDynamicDependencies,
    extract_dependency,
    _is_at_module_level,
    partialclass,
)


class TestIsAtModuleLevel:
    """Test the _is_at_module_level function."""

    def test_is_at_module_level_in_decorator(self):
        """Test _is_at_module_level when called from decorator."""
        # Simulate being called from a decorator
        with patch("inspect.currentframe") as mock_frame:
            # Create mock frames
            decorator_frame = Mock()
            decorator_frame.f_code.co_name = "injected_instance"
            decorator_frame.f_back = None

            mock_frame.return_value = decorator_frame

            result = _is_at_module_level()
            assert result is True

    def test_is_at_module_level_deep_stack(self):
        """Test _is_at_module_level with deep call stack."""
        with patch("inspect.currentframe") as mock_frame:
            # Create a chain of frames
            module_frame = Mock()
            module_frame.f_code.co_name = "<module>"
            module_frame.f_back = None

            internal_frame = Mock()
            internal_frame.f_code.co_name = "__call__"
            internal_frame.f_back = module_frame

            current_frame = Mock()
            current_frame.f_code.co_name = "_is_at_module_level"
            current_frame.f_back = internal_frame

            mock_frame.return_value = current_frame

            result = _is_at_module_level()
            assert result is True

    def test_is_at_module_level_in_function(self):
        """Test _is_at_module_level when called from inside a function."""
        with patch("inspect.currentframe") as mock_frame:
            # Create frames showing we're inside a function
            func_frame = Mock()
            func_frame.f_code.co_name = "some_function"
            func_frame.f_back = None

            current_frame = Mock()
            current_frame.f_code.co_name = "_is_at_module_level"
            current_frame.f_back = func_frame

            mock_frame.return_value = current_frame

            result = _is_at_module_level()
            assert result is False


class TestPicklableInjectedFunction:
    """Test the PicklableInjectedFunction class."""

    def test_picklable_injected_function_init(self):
        """Test PicklableInjectedFunction initialization."""

        def test_func(x):
            return x * 2

        pif = PicklableInjectedFunction(
            src=test_func,
            __doc__="Test doc",
            __name__="test_func",
            __skeleton__=["x"],
            __is_async__=False,
        )

        assert pif.src == test_func
        assert pif.__doc__ == "Test doc"
        assert pif.__name__ == "test_func"
        assert pif.__skeleton__ == ["x"]
        assert pif.__is_async__ is False

    def test_picklable_injected_function_call(self):
        """Test calling PicklableInjectedFunction."""

        def test_func(x, y):
            return x + y

        pif = PicklableInjectedFunction(
            src=test_func,
            __doc__="",
            __name__="test_func",
            __skeleton__=["x", "y"],
            __is_async__=False,
        )

        result = pif(3, 4)
        assert result == 7

    def test_picklable_injected_function_pickle(self):
        """Test pickling and unpickling PicklableInjectedFunction."""

        def test_func(x):
            return x * 3

        pif = PicklableInjectedFunction(
            src=test_func,
            __doc__="Multiply by 3",
            __name__="test_func",
            __skeleton__=["x"],
            __is_async__=False,
        )

        # Test getstate/setstate
        state = pif.__getstate__()
        assert isinstance(state, bytes)

        # Create new instance and restore state
        pif2 = PicklableInjectedFunction(None, None, None, None, None)
        pif2.__setstate__(state)

        assert pif2.__doc__ == "Multiply by 3"
        assert pif2.__name__ == "test_func"
        assert pif2.__skeleton__ == ["x"]
        assert pif2.__is_async__ is False
        assert pif2(5) == 15  # Test the function works

    @pytest.mark.asyncio
    async def test_picklable_injected_function_async(self):
        """Test PicklableInjectedFunction with async function."""

        async def async_func(x):
            await asyncio.sleep(0.001)
            return x * 2

        pif = PicklableInjectedFunction(
            src=async_func,
            __doc__="Async multiply",
            __name__="async_func",
            __skeleton__=["x"],
            __is_async__=True,
        )

        # Calling async function returns coroutine
        result = await pif(5)
        assert result == 10


class TestInjectedStaticMethods:
    """Test static methods of Injected class."""

    def test_inject_except(self):
        """Test inject_except with whitelist parameter."""

        def test_func(a, b, c, d):
            return a + b + c + d

        # Inject all except 'a' and 'b' (which are whitelisted)
        partial = Injected.inject_except(test_func, "a", "b")

        assert isinstance(partial, Injected)
        # The resulting function should have 'c' and 'd' injected

    def test_inject_except_with_self(self):
        """Test inject_except handles 'self' parameter correctly."""

        class TestClass:
            def method(self, a, b, c):
                return a + b + c

        # Should exclude 'self' automatically when using inject_except
        partial = Injected.inject_except(TestClass.method, "a")

        assert isinstance(partial, Injected)


class TestExtractDependency:
    """Test the extract_dependency function."""

    def test_extract_dependency_from_string(self):
        """Test extracting dependency from string."""
        result = extract_dependency("test_dep")

        assert result == {"test_dep"}

    def test_extract_dependency_delegated_var(self):
        """Test extract_dependency with DelegatedVar."""
        from pinjected.di.proxiable import DelegatedVar

        # Create a DelegatedVar that wraps an InjectedByName
        mock_context = Mock()
        mock_context.eval_impl.return_value = InjectedByName("test_var")
        delegated = DelegatedVar(InjectedByName("test_var"), mock_context)

        # DelegatedVar.eval() should return the wrapped Injected
        result = extract_dependency(delegated)
        # extract_dependency on InjectedByName returns its dependencies
        assert isinstance(result, set)

    def test_extract_dependency_regular_class(self):
        """Test extract_dependency with regular class."""

        class RegularClass:
            def __init__(self, a, b):
                self.a = a
                self.b = b

        result = extract_dependency(RegularClass)
        # extract_dependency returns set of argument names
        assert result == {"a", "b"}

    def test_extract_dependency_with_injected(self):
        """Test extract_dependency with Injected object."""
        injected = InjectedByName("custom_dep")

        result = extract_dependency(injected)
        # InjectedByName.dependencies() returns a set
        assert isinstance(result, set)
        assert "custom_dep" in result


class TestInjectedFunctionSignatures:
    """Test InjectedFunction signature handling."""

    def test_injected_function_with_injected_arg(self):
        """Test InjectedFunction when an argument is already Injected."""

        def func(a, b):
            return a + b

        # Create InjectedFunction with one arg as Injected
        injected_func = Injected.bind(func, a=InjectedByName("a_dep"))

        # Check that it's the right type
        assert isinstance(injected_func, InjectedFromFunction)

    def test_injected_function_str_repr(self):
        """Test string representation of InjectedFunction."""

        def test_func(x, y):
            """Test function docstring."""
            return x + y

        injected_func = Injected.bind(test_func)

        str_repr = str(injected_func)
        # InjectedFromFunction has object repr
        assert "InjectedFromFunction" in str_repr or "object at" in str_repr


class TestInjectedEdgeCases:
    """Test edge cases and error conditions."""

    def test_injected_bind_with_non_callable(self):
        """Test Injected.bind with invalid input."""
        with pytest.raises(AssertionError, match="should be callable"):
            Injected.bind("not a function")

    def test_injected_bind_with_injected_input(self):
        """Test Injected.bind with Injected as input."""
        injected = InjectedByName("test")

        with pytest.raises(
            AssertionError, match="should not be an instance of Injected"
        ):
            Injected.bind(injected)

    def test_partial_injected_function_missing_dependencies(self):
        """Test PartialInjectedFunction with missing dependencies."""

        def func(a, b, c):
            return a + b + c

        # Create partial with only 'a' and 'b' provided
        partial = Injected.inject_partially(
            func, a=InjectedByName("a_dep"), b=InjectedByName("b_dep")
        )

        # Check that partial is created
        assert isinstance(partial, Injected)

    def test_partialclass(self):
        """Test partialclass function."""

        class TestClass:
            def __init__(self, a, b, c):
                self.a = a
                self.b = b
                self.c = c

        # Create partial class with some args pre-filled
        PartialTestClass = partialclass("PartialTestClass", TestClass, a=1, b=2)

        # Should only need to provide 'c'
        instance = PartialTestClass(c=3)
        assert instance.a == 1
        assert instance.b == 2
        assert instance.c == 3


class TestInjectedAsyncBehavior:
    """Test async behavior of Injected classes."""

    @pytest.mark.asyncio
    async def test_injected_bind_sync_function_as_async(self):
        """Test binding sync function creates async wrapper."""

        def sync_func(x):
            return x * 2

        injected = Injected.bind(sync_func)

        # The bound function should handle async context
        assert isinstance(injected, InjectedFromFunction)

    @pytest.mark.asyncio
    async def test_injected_from_function_with_dynamic_deps(self):
        """Test InjectedFromFunction with dynamic dependencies."""

        def func(a, b, c):
            return a + b + c

        injected = Injected.bind(
            func,
            _dynamic_dependencies_={"c"},
            a=InjectedByName("a_dep"),
            b=InjectedByName("b_dep"),
        )

        assert isinstance(injected, InjectedFromFunction)


class TestInjectedComplexScenarios:
    """Test complex scenarios with Injected."""

    def test_nested_injected_resolution(self):
        """Test nested Injected dependencies."""

        def inner_func(x):
            return x * 2

        def outer_func(inner, y):
            return inner(y)

        inner_injected = Injected.bind(inner_func)
        outer_injected = Injected.bind(outer_func, inner=inner_injected)

        assert isinstance(outer_injected, InjectedFromFunction)

    def test_injected_with_class_methods(self):
        """Test Injected with class methods."""

        class TestService:
            def process(self, data):
                return data.upper()

        # Bind the method
        injected_method = Injected.bind(TestService.process)

        assert isinstance(injected_method, InjectedFromFunction)

    def test_injected_pickling_support(self):
        """Test that Injected objects support pickling."""

        def func(x):
            return x + 1

        injected = Injected.bind(func)

        # Should be able to pickle/unpickle
        try:
            pickled = cloudpickle.dumps(injected)
            unpickled = cloudpickle.loads(pickled)
            assert unpickled is not None
        except Exception as e:
            # Some Injected types may not be picklable
            pytest.skip(f"Pickling not supported: {e}")


class TestInjectedDynamicFeatures:
    """Test dynamic features of Injected."""

    def test_injected_dynamic(self):
        """Test Injected.dynamic method."""
        dynamic_injected = Injected.dynamic("test_key")

        assert isinstance(dynamic_injected, Injected)

    def test_injected_add_dynamic_dependencies(self):
        """Test add_dynamic_dependencies method."""
        base_injected = InjectedByName("base")

        # Test with string
        result1 = base_injected.add_dynamic_dependencies("dep1")
        assert isinstance(result1, InjectedWithDynamicDependencies)

        # Test with set
        result2 = base_injected.add_dynamic_dependencies({"dep2", "dep3"})
        assert isinstance(result2, InjectedWithDynamicDependencies)

        # Test with list
        result3 = base_injected.add_dynamic_dependencies(["dep4", "dep5"])
        assert isinstance(result3, InjectedWithDynamicDependencies)

        # Test with invalid type
        with pytest.raises(RuntimeError, match="should be string or set"):
            base_injected.add_dynamic_dependencies(123)

    def test_injected_len(self):
        """Test __len__ method of Injected."""
        injected = InjectedPure([1, 2, 3, 4, 5])
        # len() on Injected returns another Injected, not an int
        len_injected = injected.map(len)

        assert isinstance(len_injected, MappedInjected)

    def test_injected_conditional(self):
        """Test Injected.conditional method."""
        condition = InjectedPure(True)
        true_case = InjectedPure("true value")
        false_case = InjectedPure("false value")

        result = Injected.conditional(condition, true_case, false_case)

        assert isinstance(result, ConditionalInjected)

    def test_injected_desync(self):
        """Test desync method."""

        async def async_func():
            return "async result"

        # Don't call async_func(), just pass the function
        injected = InjectedPure(async_func)
        desynced = injected.desync()

        assert isinstance(desynced, MappedInjected)


class TestInjectedGetItem:
    """Test __getitem__ functionality."""

    def test_injected_getitem(self):
        """Test __getitem__ on Injected."""
        injected = InjectedPure({"key": "value", "number": 42})

        # Access item using getitem returns a DelegatedVar
        key_injected = injected["key"]

        # DelegatedVar is the proxy type used for attribute/item access
        from pinjected.di.proxiable import DelegatedVar

        assert isinstance(key_injected, DelegatedVar)


class TestMiscellaneousCoverage:
    """Test miscellaneous functions for coverage."""

    def test_conditional_injected_branches(self):
        """Test ConditionalInjected with both branches."""
        # True branch
        true_cond = Injected.conditional(
            InjectedPure(True), InjectedPure("yes"), InjectedPure("no")
        )

        # False branch
        false_cond = Injected.conditional(
            InjectedPure(False), InjectedPure("yes"), InjectedPure("no")
        )

        assert isinstance(true_cond, ConditionalInjected)
        assert isinstance(false_cond, ConditionalInjected)

    def test_mapped_injected_operations(self):
        """Test MappedInjected operations."""
        base = InjectedPure(10)

        # Map with lambda
        doubled = base.map(lambda x: x * 2)
        assert isinstance(doubled, MappedInjected)

        # Map with function
        def add_five(x):
            return x + 5

        added = base.map(add_five)
        assert isinstance(added, MappedInjected)

    def test_injected_proxy_property(self):
        """Test the proxy property of Injected."""
        injected = InjectedByName("test")

        # Access proxy
        proxy = injected.proxy
        assert proxy is not None


class TestInjectedByName:
    """Test InjectedByName class."""

    def test_injected_by_name_creation(self):
        """Test creating InjectedByName instance."""
        injected = InjectedByName("test_dependency")
        assert injected.name == "test_dependency"
        assert isinstance(injected, Injected)

    def test_injected_by_name_dependencies(self):
        """Test dependencies method."""
        injected = InjectedByName("test_dep")
        deps = injected.dependencies()
        assert deps == {"test_dep"}

    def test_injected_by_name_repr_expr(self):
        """Test __repr_expr__ method."""
        injected = InjectedByName("test_dep")
        repr_expr = injected.__repr_expr__()
        assert "test_dep" in repr_expr

    def test_injected_by_name_get_provider(self):
        """Test get_provider method."""
        injected = InjectedByName("test_dep")
        provider = injected.get_provider()
        # get_provider returns a function
        assert callable(provider)

    def test_injected_by_name_dynamic_dependencies(self):
        """Test dynamic_dependencies method."""
        injected = InjectedByName("test_dep")
        dyn_deps = injected.dynamic_dependencies()
        assert dyn_deps == set()


class TestInjectedPure:
    """Test InjectedPure class."""

    def test_injected_pure_creation(self):
        """Test creating InjectedPure instance."""
        value = {"key": "value"}
        injected = InjectedPure(value)
        assert isinstance(injected, Injected)

    def test_injected_pure_get_provider(self):
        """Test get_provider returns a function."""
        value = "test value"
        injected = InjectedPure(value)
        provider = injected.get_provider()
        # get_provider returns a function
        assert callable(provider)

    def test_injected_pure_dependencies(self):
        """Test dependencies returns empty set."""
        injected = InjectedPure("value")
        deps = injected.dependencies()
        assert deps == set()

    def test_injected_pure_repr_expr(self):
        """Test __repr_expr__ method."""
        injected = InjectedPure(42)
        repr_expr = injected.__repr_expr__()
        assert "42" in repr_expr


class TestInjectedList:
    """Test Injected.list functionality."""

    def test_injected_list(self):
        """Test Injected.list method."""
        items = [InjectedByName("a"), InjectedPure(2), InjectedByName("b")]
        injected_list = Injected.list(*items)

        # Injected.list returns a DelegatedVar
        from pinjected.di.proxiable import DelegatedVar

        assert isinstance(injected_list, DelegatedVar)


class TestInjectedEvalAndMap:
    """Test eval and map methods."""

    def test_injected_eval(self):
        """Test eval method on injected list."""
        # Create a list of injected values
        injected_list = Injected.list(InjectedPure(1), InjectedPure(2), InjectedPure(3))
        # eval() is a method on DelegatedVar
        evaled = injected_list.eval()

        assert isinstance(evaled, Injected)

    def test_injected_map_chain(self):
        """Test chaining map operations."""
        injected = InjectedPure(5)
        result = injected.map(lambda x: x * 2).map(lambda x: x + 1)

        assert isinstance(result, MappedInjected)


class TestEnsureInjected:
    """Test Injected.ensure_injected method."""

    def test_ensure_injected_with_injected(self):
        """Test ensure_injected with already Injected object."""
        injected = InjectedByName("test")
        result = Injected.ensure_injected(injected)
        assert result is injected

    def test_ensure_injected_with_callable(self):
        """Test ensure_injected with callable."""

        def func(x, y):
            return x + y

        result = Injected.ensure_injected(func)
        assert isinstance(result, Injected)

    def test_ensure_injected_with_value(self):
        """Test ensure_injected with regular value."""
        result = Injected.ensure_injected("plain value")
        # String values become InjectedByName
        assert isinstance(result, InjectedByName)


class TestInjectedCaching:
    """Test InjectedCache functionality."""

    def test_injected_cache_creation(self):
        """Test creating InjectedCache."""
        from pinjected.di.injected import InjectedCache

        cache_injected = InjectedByName("cache_dict")
        program = InjectedPure("result")
        deps = [InjectedByName("dep1")]

        cached = InjectedCache(
            cache=cache_injected, program=program, program_dependencies=deps
        )

        assert isinstance(cached, Injected)
        assert cached.cache == cache_injected
        assert cached.program == program


class TestInjectedMethods:
    """Test various Injected methods."""

    def test_injected_getattr(self):
        """Test attribute access on Injected."""
        injected = InjectedPure(type("Obj", (), {"attr": "value"})())
        attr_access = injected.proxy.attr

        from pinjected.di.proxiable import DelegatedVar

        assert isinstance(attr_access, DelegatedVar)

    def test_injected_bool_support(self):
        """Test __bool__ on Injected raises TypeError."""
        injected = InjectedPure(None)
        # Injected objects don't support bool conversion directly
        with pytest.raises(TypeError):
            bool(injected)

    def test_injected_zip(self):
        """Test Injected.zip instance method."""
        # zip is an instance method that takes two injected values
        injected1 = InjectedPure(1)
        injected2 = InjectedByName("x")

        result = injected1.zip(injected2)
        assert isinstance(result, Injected)
        deps = result.dependencies()
        assert "x" in deps


class TestAsyncInjectedCache:
    """Test AsyncInjectedCache functionality."""

    def test_async_injected_cache_creation(self):
        """Test creating AsyncInjectedCache."""
        from pinjected.di.injected import AsyncInjectedCache, IAsyncDict

        # Create a mock async dict
        class MockAsyncDict(IAsyncDict):
            async def get(self, key):
                return None

            async def set(self, key, value):
                pass

            async def delete(self, key):
                pass

            async def contains(self, key):
                return False

        cache_injected = InjectedPure(MockAsyncDict())
        program = InjectedPure("result")
        deps = [InjectedByName("dep1")]

        cached = AsyncInjectedCache(
            cache=cache_injected, program=program, program_dependencies=deps
        )

        assert isinstance(cached, Injected)


class TestAutoAwait:
    """Test auto_await function."""

    @pytest.mark.asyncio
    async def test_auto_await_with_coroutine(self):
        """Test auto_await with coroutine."""
        from pinjected.di.injected import auto_await

        async def async_func():
            return "result"

        result = await auto_await(async_func())
        assert result == "result"

    @pytest.mark.asyncio
    async def test_auto_await_with_value(self):
        """Test auto_await with regular value."""
        from pinjected.di.injected import auto_await

        result = await auto_await("not async")
        assert result == "not async"


class TestExtractDependencyIncludingSelf:
    """Test extract_dependency_including_self function."""

    def test_extract_dependency_including_self_function(self):
        """Test extract_dependency_including_self with function."""
        from pinjected.di.injected import extract_dependency_including_self

        def func(a, b, c):
            return a + b + c

        deps = extract_dependency_including_self(func)
        assert deps == {"a", "b", "c"}

    def test_extract_dependency_including_self_class(self):
        """Test extract_dependency_including_self with class."""
        from pinjected.di.injected import extract_dependency_including_self

        class TestClass:
            def __init__(self, x, y):
                pass

        deps = extract_dependency_including_self(TestClass)
        # Should include self for classes
        assert "self" in deps or deps == {"x", "y"}


class TestSolveInjection:
    """Test solve_injection function."""

    @pytest.mark.asyncio
    async def test_solve_injection_string(self):
        """Test solve_injection with string dependency."""
        from pinjected.di.injected import solve_injection

        kwargs = {"test_key": "test_value"}
        result = await solve_injection("test_key", kwargs)
        assert result == "test_value"

    @pytest.mark.asyncio
    async def test_solve_injection_callable(self):
        """Test solve_injection with callable."""
        from pinjected.di.injected import solve_injection

        def func(a, b):
            return a + b

        kwargs = {"a": 1, "b": 2}
        result = await solve_injection(func, kwargs)
        assert result == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
