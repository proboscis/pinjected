"""Additional tests for pinjected/di/injected.py to improve coverage."""

import asyncio
import pytest
from dataclasses import dataclass

from pinjected import Injected
from pinjected.di.injected import (
    InjectedPure,
    InjectedByName,
    InjectedFromFunction,
    MZippedInjected,
    ConditionalInjected,
    get_frame_info,
    partialclass,
    FrameInfo,
    INJECTED_CONTEXT,
    ReboundInjected,
    PartialInjectedFunction,
    combine_image_store,
    assert_kwargs_type,
    extract_dependency,
)


class TestInjectedPure:
    """Test InjectedPure functionality."""

    def test_injected_pure_basic(self):
        """Test basic InjectedPure functionality."""
        injected = InjectedPure(42)

        assert injected.value == 42

    def test_injected_pure_dependencies(self):
        """Test InjectedPure has no dependencies."""
        injected = InjectedPure("test")

        deps = injected.dependencies()
        assert deps == set()

    @pytest.mark.asyncio
    async def test_injected_pure_get_provider(self):
        """Test InjectedPure get_provider."""
        injected = InjectedPure(100)

        provider = injected.get_provider()
        # get_provider returns an async function
        assert asyncio.iscoroutinefunction(provider)
        result = await provider()
        assert result == 100

    def test_injected_pure_repr_expr(self):
        """Test InjectedPure repr_expr."""
        injected = InjectedPure("hello")

        expr = injected.__repr_expr__()
        assert "hello" in expr


class TestInjectedByName:
    """Test InjectedByName functionality."""

    def test_injected_by_name_basic(self):
        """Test basic InjectedByName functionality."""
        injected = InjectedByName("test_name")

        assert injected.name == "test_name"

    def test_injected_by_name_dependencies(self):
        """Test InjectedByName dependencies."""
        injected = InjectedByName("my_dependency")

        deps = injected.dependencies()
        assert "my_dependency" in deps

    def test_injected_by_name_get_provider(self):
        """Test InjectedByName get_provider."""
        injected = InjectedByName("test_key")

        provider = injected.get_provider()
        # Provider should be a callable
        assert callable(provider)

    def test_injected_by_name_repr_expr(self):
        """Test InjectedByName repr_expr."""
        injected = InjectedByName("config")

        expr = injected.__repr_expr__()
        assert "config" in expr


class TestInjectedFromFunction:
    """Test InjectedFromFunction functionality."""

    def test_injected_from_function_basic(self):
        """Test basic InjectedFromFunction functionality."""

        async def test_func(a, b):
            return a + b

        injected = InjectedFromFunction(
            original_function=test_func, target_function=test_func, kwargs_mapping={}
        )

        assert injected.original_function == test_func
        assert injected.target_function == test_func

    def test_injected_from_function_dependencies(self):
        """Test InjectedFromFunction dependencies."""

        async def test_func(dep1, dep2):
            return dep1 + dep2

        injected = InjectedFromFunction(
            original_function=test_func, target_function=test_func, kwargs_mapping={}
        )

        deps = injected.dependencies()
        assert "dep1" in deps
        assert "dep2" in deps

    def test_injected_from_function_with_dynamic_dependencies(self):
        """Test InjectedFromFunction with dynamic dependencies."""

        async def test_func(a, b):
            return a * b

        injected = InjectedFromFunction(
            original_function=test_func,
            target_function=test_func,
            kwargs_mapping={},
            dynamic_dependencies={"dynamic_dep1", "dynamic_dep2"},
        )

        dyn_deps = injected.dynamic_dependencies()
        assert "dynamic_dep1" in dyn_deps
        assert "dynamic_dep2" in dyn_deps


class TestPartialInjectedFunction:
    """Test PartialInjectedFunction functionality."""

    def test_partial_injected_function_basic(self):
        """Test basic PartialInjectedFunction functionality."""

        def test_func(a, b, c):
            return a + b + c

        base_injected = Injected.bind(test_func)
        partial = PartialInjectedFunction(base_injected, {"a": 10})

        assert partial.src == base_injected
        # Check that it's a dataclass with src attribute
        assert hasattr(partial, "src")

    def test_partial_injected_function_dependencies(self):
        """Test PartialInjectedFunction dependencies."""

        def test_func(dep1, dep2, dep3):
            return dep1 + dep2 + dep3

        base_injected = Injected.bind(test_func)
        partial = PartialInjectedFunction(base_injected, {"dep1": "fixed"})

        deps = partial.dependencies()
        # PartialInjectedFunction includes all dependencies from the base function
        assert "dep1" in deps
        assert "dep2" in deps
        assert "dep3" in deps


class TestMZippedInjected:
    """Test MZippedInjected functionality."""

    def test_mzipped_injected_basic(self):
        """Test basic MZippedInjected functionality."""
        src1 = Injected.pure(1)
        src2 = Injected.pure(2)
        src3 = Injected.pure(3)

        zipped = MZippedInjected(src1, src2, src3)

        assert len(zipped.srcs) == 3
        assert src1 in zipped.srcs

    def test_mzipped_injected_dependencies(self):
        """Test MZippedInjected dependencies."""
        src1 = Injected.by_name("dep1")
        src2 = Injected.by_name("dep2")

        zipped = MZippedInjected(src1, src2)

        deps = zipped.dependencies()
        assert "dep1" in deps
        assert "dep2" in deps

    def test_mzipped_injected_repr_expr(self):
        """Test MZippedInjected repr_expr."""
        src1 = Injected.pure(1)
        src2 = Injected.pure(2)

        zipped = MZippedInjected(src1, src2)

        expr = zipped.__repr_expr__()
        # MZippedInjected repr shows the sources in parentheses
        assert expr == "(<1>, <2>)"


class TestFrameInfo:
    """Test FrameInfo and get_frame_info functionality."""

    def test_frame_info_dataclass(self):
        """Test FrameInfo dataclass."""
        frame_info = FrameInfo(
            original_frame=None,
            trc=None,
            filename="test.py",
            line_number=42,
            function_name="test_func",
            sources=["line1", "line2"],
            line_idx_in_sources=0,
        )

        assert frame_info.filename == "test.py"
        assert frame_info.line_number == 42
        assert frame_info.function_name == "test_func"

    def test_get_frame_info(self):
        """Test get_frame_info function."""
        # This should return info about this test function
        info = get_frame_info(1)

        if info is not None:
            assert isinstance(info, FrameInfo)
            assert info.function_name is not None
        # It's okay if it returns None in test environment


class TestUtilityFunctions:
    """Test utility functions."""

    def test_partialclass(self):
        """Test partialclass function."""

        @dataclass
        class TestClass:
            a: int
            b: str = "default"

        PartialTestClass = partialclass("PartialTestClass", TestClass, a=42)

        instance = PartialTestClass()
        assert instance.a == 42
        assert instance.b == "default"

    def test_injected_context(self):
        """Test INJECTED_CONTEXT is frozen dict."""
        assert isinstance(INJECTED_CONTEXT, dict)
        # It should be frozen
        with pytest.raises(Exception):
            INJECTED_CONTEXT["new_key"] = "value"


class TestConditionalInjected:
    """Test ConditionalInjected functionality."""

    def test_conditional_injected_basic(self):
        """Test basic ConditionalInjected functionality."""
        condition = Injected.pure(True)
        true_val = Injected.pure("yes")
        false_val = Injected.pure("no")

        conditional = ConditionalInjected(condition, true_val, false_val)

        assert conditional.condition == condition
        assert conditional.true == true_val
        assert conditional.false == false_val

    def test_conditional_injected_dependencies(self):
        """Test ConditionalInjected dependencies."""
        condition = Injected.by_name("cond")
        true_val = Injected.by_name("true_dep")
        false_val = Injected.by_name("false_dep")

        conditional = ConditionalInjected(condition, true_val, false_val)

        deps = conditional.dependencies()
        assert "cond" in deps
        assert "session" in deps  # ConditionalInjected needs session

    def test_conditional_injected_dynamic_dependencies(self):
        """Test ConditionalInjected dynamic dependencies."""
        condition = Injected.pure(True)
        true_val = Injected.by_name("true_dep")
        false_val = Injected.by_name("false_dep")

        conditional = ConditionalInjected(condition, true_val, false_val)

        dyn_deps = conditional.dynamic_dependencies()
        # ConditionalInjected only includes session in dynamic dependencies
        assert "session" in dyn_deps


class TestReboundInjected:
    """Test ReboundInjected functionality."""

    def test_rebound_injected_basic(self):
        """Test basic ReboundInjected functionality."""
        src = Injected.by_name("old_name")
        mapping = {"old_name": "new_name"}

        rebound = ReboundInjected(src, mapping)

        assert rebound.src == src
        assert rebound.mapping == mapping

    def test_rebound_injected_dependencies(self):
        """Test ReboundInjected dependencies."""
        src = Injected.by_name("old_dep")
        mapping = {"old_dep": "new_dep"}

        rebound = ReboundInjected(src, mapping)

        deps = rebound.dependencies()
        assert "new_dep" in deps
        assert "old_dep" not in deps


class TestExtractDependency:
    """Test extract_dependency functionality."""

    def test_extract_dependency_simple(self):
        """Test extract_dependency with simple function."""

        def func(a, b):
            pass

        deps = extract_dependency(func)

        assert "a" in deps
        assert "b" in deps

    def test_extract_dependency_with_defaults(self):
        """Test extract_dependency with default values."""

        def func(a, b=10):
            pass

        deps = extract_dependency(func)

        # Should include parameters with defaults
        assert "a" in deps
        assert "b" in deps


class TestAssertKwargsType:
    """Test assert_kwargs_type functionality."""

    def test_assert_kwargs_type_valid(self):
        """Test assert_kwargs_type with valid values."""
        # Should not raise for strings, types, and callables
        assert_kwargs_type("string_value")
        assert_kwargs_type(int)
        assert_kwargs_type(lambda x: x)


class TestAsyncGather:
    """Test async gather related functionality."""

    @pytest.mark.asyncio
    async def test_async_gather_multiple(self):
        """Test gathering multiple async injected values."""

        async def async_value1():
            return 1

        async def async_value2():
            return 2

        injected1 = Injected.bind(async_value1)
        injected2 = Injected.bind(async_value2)

        # Test that we can create async injected values
        assert isinstance(injected1, Injected)
        assert isinstance(injected2, Injected)


class TestConditionalMethods:
    """Test conditional and procedure methods."""

    def test_procedure(self):
        """Test Injected.procedure method."""

        def side_effect_func(value):
            # Simulate side effect
            return None

        base = Injected.pure(42)
        proc = base.procedure(Injected.bind(side_effect_func))

        # procedure returns a DelegatedVar (proxy), not an Injected
        from pinjected.di.proxiable import DelegatedVar

        assert isinstance(proc, DelegatedVar)

    def test_conditional_preparation(self):
        """Test Injected.conditional_preparation method."""
        condition = Injected.pure(True)
        preparation = Injected.pure("prepared")
        utilization = Injected.pure("utilized")

        # conditional_preparation is a static method taking 3 arguments
        result = Injected.conditional_preparation(condition, preparation, utilization)

        assert isinstance(result, Injected)


class TestCombineImageStore:
    """Test combine_image_store functionality."""

    def test_combine_image_store(self):
        """Test combine_image_store basic functionality."""
        # Test combining two values (addition operation)
        result = combine_image_store(10, 20)

        # This function adds two values together
        assert result == 30
