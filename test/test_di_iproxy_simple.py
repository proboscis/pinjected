"""Simple tests for di/iproxy.py module."""

import pytest
from typing import TypeVar

from pinjected.di.iproxy import IProxy, T
from pinjected.di.proxiable import DelegatedVar
from pinjected.di.app_injected import InjectedEvalContext
from pinjected.di.expr_util import Object


class TestIProxy:
    """Test the IProxy class."""

    def test_iproxy_class_exists(self):
        """Test that IProxy class exists."""
        assert IProxy is not None
        assert isinstance(IProxy, type)

    def test_iproxy_inherits_from_delegated_var(self):
        """Test that IProxy inherits from DelegatedVar."""
        assert issubclass(IProxy, DelegatedVar)

    def test_iproxy_type_variable(self):
        """Test that T type variable is defined."""
        assert T is not None
        assert isinstance(T, TypeVar)
        assert T.__name__ == "T"

    def test_iproxy_instantiation_with_int(self):
        """Test creating IProxy with an integer."""
        proxy = IProxy(42)

        assert proxy is not None
        assert isinstance(proxy, IProxy)
        assert isinstance(proxy, DelegatedVar)

        # Check internal structure
        assert hasattr(proxy, "__value__")
        assert hasattr(proxy, "__cxt__")

    def test_iproxy_instantiation_with_string(self):
        """Test creating IProxy with a string."""
        proxy = IProxy("hello")

        assert proxy is not None
        assert isinstance(proxy, IProxy)

    def test_iproxy_instantiation_with_list(self):
        """Test creating IProxy with a list."""
        proxy = IProxy([1, 2, 3])

        assert proxy is not None
        assert isinstance(proxy, IProxy)

    def test_iproxy_instantiation_with_dict(self):
        """Test creating IProxy with a dict."""
        proxy = IProxy({"key": "value"})

        assert proxy is not None
        assert isinstance(proxy, IProxy)

    def test_iproxy_instantiation_with_none(self):
        """Test creating IProxy with None."""
        proxy = IProxy(None)

        assert proxy is not None
        assert isinstance(proxy, IProxy)

    def test_iproxy_internal_value_is_object(self):
        """Test that internal value is wrapped in Object."""
        value = 42
        proxy = IProxy(value)

        # __value__ should be an Object instance
        assert isinstance(proxy.__value__, Object)
        assert proxy.__value__.data == value

    def test_iproxy_internal_context(self):
        """Test that internal context is InjectedEvalContext."""
        proxy = IProxy("test")

        # __cxt__ should be InjectedEvalContext
        assert proxy.__cxt__ is InjectedEvalContext

    def test_iproxy_with_custom_object(self):
        """Test creating IProxy with custom object."""

        class CustomClass:
            def __init__(self, x):
                self.x = x

        obj = CustomClass(10)
        proxy = IProxy(obj)

        assert proxy is not None
        assert isinstance(proxy, IProxy)
        assert proxy.__value__.data is obj

    def test_iproxy_multiple_instances(self):
        """Test creating multiple IProxy instances."""
        proxy1 = IProxy(1)
        proxy2 = IProxy(2)
        proxy3 = IProxy(1)

        # All should be IProxy instances
        assert all(isinstance(p, IProxy) for p in [proxy1, proxy2, proxy3])

        # They should be different objects
        assert proxy1 is not proxy2
        assert proxy1 is not proxy3
        assert proxy2 is not proxy3

    def test_iproxy_type_generic(self):
        """Test that IProxy is generic."""
        # Type annotations should work
        int_proxy: IProxy[int] = IProxy(42)
        str_proxy: IProxy[str] = IProxy("hello")

        assert isinstance(int_proxy, IProxy)
        assert isinstance(str_proxy, IProxy)

    def test_iproxy_with_function(self):
        """Test creating IProxy with a function."""

        def my_func(x):
            return x * 2

        proxy = IProxy(my_func)

        assert proxy is not None
        assert isinstance(proxy, IProxy)
        assert proxy.__value__.data is my_func


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
