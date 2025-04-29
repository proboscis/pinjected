import pytest

from pinjected import Injected, IProxy, design
from pinjected.v2.async_resolver import AsyncResolver


@pytest.mark.asyncio
async def test_iproxy_constructor_equivalence():
    """
    Test that IProxy(value) works the same as Injected.pure(value).proxy
    """
    # Test with primitive values
    value1 = 42
    value2 = "test string"
    value3 = [1, 2, 3]
    value4 = {"a": 1, "b": 2}
    
    # Create using both methods
    ip1 = IProxy(value1)
    ip2 = IProxy(value2)
    ip3 = IProxy(value3)
    ip4 = IProxy(value4)
    
    ip1_alt = Injected.pure(value1).proxy
    ip2_alt = Injected.pure(value2).proxy
    ip3_alt = Injected.pure(value3).proxy
    ip4_alt = Injected.pure(value4).proxy
    
    # Create complex expressions with both
    expr1 = ip1 + 10
    expr1_alt = ip1_alt + 10
    
    expr2 = ip2 + " appended"
    expr2_alt = ip2_alt + " appended"
    
    expr3 = ip3[1]
    expr3_alt = ip3_alt[1]
    
    expr4 = ip4["a"]
    expr4_alt = ip4_alt["a"]
    
    # Design with all expressions
    test_design = design(
        ip1=ip1,
        ip1_alt=ip1_alt,
        ip2=ip2,
        ip2_alt=ip2_alt,
        ip3=ip3,
        ip3_alt=ip3_alt,
        ip4=ip4,
        ip4_alt=ip4_alt,
        expr1=expr1,
        expr1_alt=expr1_alt,
        expr2=expr2,
        expr2_alt=expr2_alt,
        expr3=expr3,
        expr3_alt=expr3_alt,
        expr4=expr4,
        expr4_alt=expr4_alt
    )
    
    # Resolve and compare
    resolver = AsyncResolver(test_design)
    
    # Compare base values
    assert await resolver.provide("ip1") == await resolver.provide("ip1_alt")
    assert await resolver.provide("ip2") == await resolver.provide("ip2_alt")
    assert await resolver.provide("ip3") == await resolver.provide("ip3_alt")
    assert await resolver.provide("ip4") == await resolver.provide("ip4_alt")
    
    # Compare expressions
    assert await resolver.provide("expr1") == await resolver.provide("expr1_alt")
    assert await resolver.provide("expr2") == await resolver.provide("expr2_alt")
    assert await resolver.provide("expr3") == await resolver.provide("expr3_alt")
    assert await resolver.provide("expr4") == await resolver.provide("expr4_alt")
    
    # Check the actual values
    assert await resolver.provide("ip1") == value1
    assert await resolver.provide("ip2") == value2
    assert await resolver.provide("ip3") == value3
    assert await resolver.provide("ip4") == value4


@pytest.mark.asyncio
async def test_iproxy_constructor_with_complex_objects():
    """
    Test IProxy constructor with more complex objects and operations
    """
    class TestObj:
        def __init__(self, value):
            self.value = value
        
        def get_value(self):
            return self.value
        
        def multiply(self, factor):
            return self.value * factor
    
    # Create test objects
    obj1 = TestObj(100)
    
    # Create IProxy objects both ways
    ip_obj1 = IProxy(obj1)
    ip_obj1_alt = Injected.pure(obj1).proxy
    
    # Access attributes and methods
    attr1 = ip_obj1.value
    attr1_alt = ip_obj1_alt.value
    
    method1 = ip_obj1.get_value()
    method1_alt = ip_obj1_alt.get_value()
    
    method2 = ip_obj1.multiply(5)
    method2_alt = ip_obj1_alt.multiply(5)
    
    # Complex expressions
    complex1 = ip_obj1.value + IProxy(50)
    complex1_alt = ip_obj1_alt.value + Injected.pure(50).proxy
    
    # Create design and resolve
    test_design = design(
        ip_obj1=ip_obj1,
        ip_obj1_alt=ip_obj1_alt,
        attr1=attr1,
        attr1_alt=attr1_alt,
        method1=method1,
        method1_alt=method1_alt,
        method2=method2,
        method2_alt=method2_alt,
        complex1=complex1,
        complex1_alt=complex1_alt
    )
    
    resolver = AsyncResolver(test_design)
    
    # Compare base values
    assert await resolver.provide("ip_obj1") == await resolver.provide("ip_obj1_alt")
    
    # Compare attributes and methods
    assert await resolver.provide("attr1") == await resolver.provide("attr1_alt")
    assert await resolver.provide("method1") == await resolver.provide("method1_alt")
    assert await resolver.provide("method2") == await resolver.provide("method2_alt")
    
    # Compare complex expressions
    assert await resolver.provide("complex1") == await resolver.provide("complex1_alt")
    
    # Check expected values
    assert await resolver.provide("attr1") == 100
    assert await resolver.provide("method1") == 100
    assert await resolver.provide("method2") == 500
    assert await resolver.provide("complex1") == 150


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_iproxy_constructor_equivalence())
    asyncio.run(test_iproxy_constructor_with_complex_objects())
