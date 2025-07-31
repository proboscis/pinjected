import pytest

from pinjected import Injected, design
from pinjected.di.iproxy import IProxy
from pinjected.v2.async_resolver import AsyncResolver


@pytest.mark.asyncio
async def test_iproxy_tuple():
    """Test IProxy.tuple() static method with various input types."""
    # Test with IProxy instances
    a = IProxy(1)
    b = IProxy(2)
    c = IProxy(3)
    tuple_proxy = IProxy.tuple(a, b, c)

    # Test with mixed IProxy, Injected, and plain values
    d = Injected.by_name("d_value")
    mixed_tuple = IProxy.tuple(a, d, 4, "hello")

    # Create design and resolver
    test_design = design(
        d_value=10, tuple_result=tuple_proxy.eval(), mixed_result=mixed_tuple.eval()
    )

    resolver = AsyncResolver(test_design)

    # Verify results
    assert await resolver.provide("tuple_result") == (1, 2, 3)
    assert await resolver.provide("mixed_result") == (1, 10, 4, "hello")


@pytest.mark.asyncio
async def test_iproxy_dict():
    """Test IProxy.dict() static method with various input types."""
    # Test with IProxy instances
    a = IProxy(100)
    b = IProxy(200)
    dict_proxy = IProxy.dict(key_a=a, key_b=b)

    # Test with mixed IProxy, Injected, and plain values
    c = Injected.by_name("c_value")
    mixed_dict = IProxy.dict(x=a, y=c, z=300, name="test")

    # Create design and resolver
    test_design = design(
        c_value=50, dict_result=dict_proxy.eval(), mixed_dict_result=mixed_dict.eval()
    )

    resolver = AsyncResolver(test_design)

    # Verify results
    assert await resolver.provide("dict_result") == {"key_a": 100, "key_b": 200}
    assert await resolver.provide("mixed_dict_result") == {
        "x": 100,
        "y": 50,
        "z": 300,
        "name": "test",
    }


@pytest.mark.asyncio
async def test_iproxy_list():
    """Test IProxy.list() static method with various input types."""
    # Test with IProxy instances
    a = IProxy(10)
    b = IProxy(20)
    c = IProxy(30)
    list_proxy = IProxy.list(a, b, c)

    # Test with mixed IProxy, Injected, and plain values
    d = Injected.by_name("d_value")
    mixed_list = IProxy.list(a, d, 40, "world")

    # Create design and resolver
    test_design = design(
        d_value=25, list_result=list_proxy.eval(), mixed_list_result=mixed_list.eval()
    )

    resolver = AsyncResolver(test_design)

    # Verify results
    assert await resolver.provide("list_result") == [10, 20, 30]
    assert await resolver.provide("mixed_list_result") == [10, 25, 40, "world"]


@pytest.mark.asyncio
async def test_iproxy_procedure():
    """Test IProxy.procedure() static method."""
    # Create a list to track side effects
    effects = []

    def setup():
        effects.append("setup")
        return "setup_done"

    def main_task():
        effects.append("main")
        return "main_result"

    def cleanup():
        effects.append("cleanup")
        return "cleanup_done"

    # Create Injected instances (not IProxy wrapping them)
    setup_injected = Injected.bind(setup)
    main_injected = Injected.bind(main_task)
    cleanup_injected = Injected.bind(cleanup)

    # Create procedure using Injected instances directly
    procedure_result = IProxy.procedure(setup_injected, main_injected, cleanup_injected)

    # Create design and resolver
    test_design = design(procedure=procedure_result.eval())

    resolver = AsyncResolver(test_design)

    # Execute procedure
    result = await resolver.provide("procedure")

    # Verify it returns the last result
    assert result == "cleanup_done"
    # Note: The order of side effects may vary due to async execution,
    # but all should be executed
    assert set(effects) == {"setup", "main", "cleanup"}


@pytest.mark.asyncio
async def test_iproxy_procedure_empty():
    """Test IProxy.procedure() with no arguments."""
    empty_procedure = IProxy.procedure()

    test_design = design(empty_result=empty_procedure.eval())

    resolver = AsyncResolver(test_design)

    # Empty procedure should return None
    assert await resolver.provide("empty_result") is None


@pytest.mark.asyncio
async def test_iproxy_procedure_with_injected():
    """Test IProxy.procedure() with Injected instances."""
    results = []

    def task1():
        results.append("task1")
        return "result1"

    def task2():
        results.append("task2")
        return "result2"

    def task3():
        results.append("task3")
        return "result3"

    # Create Injected instances
    inj1 = Injected.bind(task1)
    inj2 = Injected.bind(task2)
    inj3 = Injected.bind(task3)

    # Create procedure with Injected instances
    procedure_result = IProxy.procedure(inj1, inj2, inj3)

    test_design = design(final_result=procedure_result.eval())

    resolver = AsyncResolver(test_design)

    # Should return the last value
    result = await resolver.provide("final_result")
    assert result == "result3"
    # All tasks should have been executed
    assert len(results) == 3


@pytest.mark.asyncio
async def test_iproxy_procedure_type_error():
    """Test IProxy.procedure() raises TypeError for invalid input."""
    with pytest.raises(
        TypeError, match="procedure only accepts IProxy or Injected instances"
    ):
        IProxy.procedure(IProxy(1), "invalid_string", IProxy(3))


@pytest.mark.asyncio
async def test_complex_composition():
    """Test complex composition of IProxy static methods."""
    # Create some base values
    a = IProxy(1)
    b = Injected.by_name("b_value")
    c = IProxy(3)

    # Create complex nested structure
    inner_dict = IProxy.dict(x=a, y=b)
    inner_list = IProxy.list(c, 4, 5)
    complex_tuple = IProxy.tuple(inner_dict, inner_list, "extra")

    # Create design and resolver
    test_design = design(b_value=2, complex_result=complex_tuple.eval())

    resolver = AsyncResolver(test_design)

    # Verify the complex nested structure
    result = await resolver.provide("complex_result")
    assert result == ({"x": 1, "y": 2}, [3, 4, 5], "extra")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
