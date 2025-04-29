import pytest

from pinjected import Injected, design
from pinjected.v2.async_resolver import AsyncResolver


class TestObject:
    """Test object with attributes and methods for IProxy testing."""
    
    def __init__(self, value):
        self.value = value
        self.items = {"a": 1, "b": 2, "c": 3}
    
    def multiply(self, factor):
        return self.value * factor
    
    def __str__(self):
        return f"TestObject({self.value})"


@pytest.mark.asyncio
async def test_iproxy_composition():
    """
    Test case for composing multiple IProxy objects with various operations
    (add, getitem, call, div, attribute access) and evaluating them with AsyncResolver.
    """
    num1 = Injected.pure(10).proxy
    num2 = Injected.pure(5).proxy
    test_obj = Injected.pure(TestObject(20)).proxy
    test_dict = Injected.pure({"x": 100, "y": 200, "z": 300}).proxy
    test_func = Injected.pure(lambda x: x * 2).proxy
    
    add_result = num1 + num2  # Should be 15
    
    div_result = num1 / num2  # Should be 2
    
    attr_access = test_obj.value  # Should be 20
    
    method_call = test_obj.multiply(3)  # Should be 60
    
    getitem_result = test_dict[Injected.pure("y").proxy]  # Should be 200
    
    func_call = test_func(num2)  # Should be 10
    
    complex_expr = (num1 + test_obj.value) / num2 + test_dict[Injected.pure("x").proxy]
    
    test_design = design(
        num1=num1,
        num2=num2,
        test_obj=test_obj,
        test_dict=test_dict,
        test_func=test_func,
        add_result=add_result,
        div_result=div_result,
        attr_access=attr_access,
        method_call=method_call,
        getitem_result=getitem_result,
        func_call=func_call,
        complex_expr=complex_expr
    )
    
    resolver = AsyncResolver(test_design)
    
    assert await resolver.provide("num1") == 10
    assert await resolver.provide("num2") == 5
    assert isinstance(await resolver.provide("test_obj"), TestObject)
    
    assert await resolver.provide("add_result") == 15
    assert await resolver.provide("div_result") == 2
    assert await resolver.provide("attr_access") == 20
    assert await resolver.provide("method_call") == 60
    assert await resolver.provide("getitem_result") == 200
    assert await resolver.provide("func_call") == 10
    assert await resolver.provide("complex_expr") == 106


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_iproxy_composition())
