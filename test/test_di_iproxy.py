"""Tests for di.iproxy module."""

from pinjected.di.iproxy import IProxy
from pinjected.di.proxiable import DelegatedVar
from pinjected.di.expr_util import Object
from pinjected.di.app_injected import InjectedEvalContext


class TestIProxy:
    """Test IProxy class."""

    # Basic instantiation tests removed - comprehensively covered in test_iproxy_constructor.py

    def test_instantiation_with_object(self):
        """Test IProxy instantiation with custom objects."""

        class CustomObject:
            def __init__(self, value):
                self.value = value

        obj = CustomObject(100)
        proxy = IProxy(obj)
        assert isinstance(proxy, IProxy)
        assert isinstance(proxy, DelegatedVar)

    def test_internal_structure(self):
        """Test the internal structure of IProxy."""
        value = "test"
        proxy = IProxy(value)

        # Check that __value__ is an Object wrapping the value
        assert hasattr(proxy, "__value__")
        assert isinstance(proxy.__value__, Object)
        # Object stores the value in its data attribute
        assert proxy.__value__.data == value

        # Check that __cxt__ is InjectedEvalContext
        assert hasattr(proxy, "__cxt__")
        assert proxy.__cxt__ is InjectedEvalContext

    def test_with_none(self):
        """Test IProxy with None value."""
        proxy = IProxy(None)
        assert isinstance(proxy, IProxy)
        assert proxy.__value__.data is None

    # test_with_different_types removed - covered in test_iproxy_constructor.py

    def test_type_parameter(self):
        """Test that IProxy preserves type parameter."""
        # This is mainly for static type checking, but we can verify
        # that the proxy is created successfully
        proxy_int: IProxy[int] = IProxy(42)
        proxy_str: IProxy[str] = IProxy("hello")
        proxy_list: IProxy[list[int]] = IProxy([1, 2, 3])

        assert isinstance(proxy_int, IProxy)
        assert isinstance(proxy_str, IProxy)
        assert isinstance(proxy_list, IProxy)
