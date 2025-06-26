"""Tests for IProxy pytest introspection attribute handling"""

import pytest
from pinjected import IProxy, design
from pinjected.v2.async_resolver import AsyncResolver


def test_iproxy_pytest_introspection_attributes():
    """Test that IProxy properly handles pytest introspection attributes without loops"""

    # Create an IProxy instance
    test_obj = IProxy(lambda: "test function")

    # Test pytest introspection attributes that would go through __getattr__
    # (excluding those that exist on the IProxy class itself like __module__, __name__, etc.)
    introspection_attrs = [
        "__signature__",
        "signature",
        "__wrapped__",
        "im_func",
        "func",
        "__func__",
    ]

    for attr in introspection_attrs:
        # These should raise AttributeError instead of causing loops
        try:
            _ = getattr(test_obj, attr)
            assert False, f"Should have raised AttributeError for {attr}"
        except AttributeError as e:
            # Check for either IProxy or DelegatedVar in the error message
            error_msg = str(e)
            assert (
                "'IProxy' object has no attribute" in error_msg
                or "'DelegatedVar' object has no attribute" in error_msg
            )

        # Also verify hasattr returns False
        assert not hasattr(test_obj, attr)


@pytest.mark.asyncio
async def test_iproxy_normal_attribute_access():
    """Test that normal attribute access still works through delegation"""

    class TestClass:
        def __init__(self):
            self.value = 42
            self.name = "test"

        def method(self):
            return "method result"

    # Create IProxy instance
    obj = TestClass()
    proxy = IProxy(obj)

    # Normal attribute access should still work through delegation
    # Create a design with the proxy expressions
    d = design(value=proxy.value, name=proxy.name, method_result=proxy.method())

    # Resolve the design
    resolver = AsyncResolver(d)
    assert await resolver.provide("value") == 42
    assert await resolver.provide("name") == "test"
    assert await resolver.provide("method_result") == "method result"


def test_iproxy_with_test_prefix_discovery():
    """Test that IProxy objects with 'test' prefix don't cause pytest collection issues"""

    # This simulates what happens when pytest discovers a 'test_' prefixed IProxy
    test_my_function = IProxy(lambda: "test result")

    # Pytest would try to access these attributes during collection
    # They should fail gracefully with AttributeError
    try:
        _ = test_my_function.__signature__
        assert False, "Should have raised AttributeError"
    except AttributeError:
        pass

    # Also verify hasattr returns False for pytest introspection attributes
    assert not hasattr(test_my_function, "__signature__")
    assert not hasattr(test_my_function, "__wrapped__")


def test_iproxy_prevents_introspection_loops():
    """Test that introspection doesn't cause infinite loops"""

    class RecursiveClass:
        def __getattr__(self, item):
            # This could cause loops if not handled properly
            return getattr(self, f"_{item}")

    proxy = IProxy(RecursiveClass())

    # These should raise AttributeError immediately, not cause loops
    with pytest.raises(AttributeError):
        _ = proxy.__signature__

    with pytest.raises(AttributeError):
        _ = proxy.__name__
