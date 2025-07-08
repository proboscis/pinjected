"""Simple tests for di/dynamic_proxy.py module to improve coverage."""

import pytest
from unittest.mock import Mock
from dataclasses import is_dataclass

from pinjected.di.dynamic_proxy import DynamicProxyContextImpl, DynamicProxyIterator
from pinjected.di.proxiable import DelegatedVar


class TestDynamicProxyContextImpl:
    """Test the DynamicProxyContextImpl class."""

    def test_dynamic_proxy_context_impl_is_dataclass(self):
        """Test that DynamicProxyContextImpl is a dataclass."""
        assert is_dataclass(DynamicProxyContextImpl)

    def test_dynamic_proxy_context_impl_creation(self):
        """Test creating DynamicProxyContextImpl instance."""

        def accessor(x):
            return x.upper()

        def pure_impl(x):
            return f"Pure({x})"

        proxy_ctx = DynamicProxyContextImpl(
            accessor=accessor, pure_impl=pure_impl, _alias_name="TestProxy"
        )

        assert proxy_ctx.accessor is accessor
        assert proxy_ctx.pure_impl is pure_impl
        assert proxy_ctx._alias_name == "TestProxy"

    def test_getattr(self):
        """Test getattr method."""
        # Create a mock object with attributes
        mock_obj = Mock()
        mock_obj.test_attr = "test_value"

        def accessor(x):
            return x

        def pure_impl(x):
            return f"Pure({x})"

        proxy_ctx = DynamicProxyContextImpl(
            accessor=accessor, pure_impl=pure_impl, _alias_name="TestProxy"
        )

        result = proxy_ctx.getattr(mock_obj, "test_attr")

        assert isinstance(result, DelegatedVar)
        assert result.value == "Pure(test_value)"
        assert result.__cxt__ is proxy_ctx

    def test_call(self):
        """Test call method."""
        # Create a callable mock
        mock_callable = Mock(return_value="call_result")

        def accessor(x):
            return x

        def pure_impl(x):
            return f"Pure({x})"

        proxy_ctx = DynamicProxyContextImpl(
            accessor=accessor, pure_impl=pure_impl, _alias_name="TestProxy"
        )

        result = proxy_ctx.call(mock_callable, "arg1", "arg2", kwarg="value")

        mock_callable.assert_called_once_with("arg1", "arg2", kwarg="value")
        assert isinstance(result, DelegatedVar)
        assert result.value == "Pure(call_result)"

    def test_pure(self):
        """Test pure method."""

        def accessor(x):
            return x

        def pure_impl(x):
            return f"Pure({x})"

        proxy_ctx = DynamicProxyContextImpl(
            accessor=accessor, pure_impl=pure_impl, _alias_name="TestProxy"
        )

        result = proxy_ctx.pure("test_value")

        assert isinstance(result, DelegatedVar)
        assert result.value == "Pure(test_value)"
        assert result.__cxt__ is proxy_ctx

    def test_getitem(self):
        """Test getitem method."""
        # Create a mock object with subscript support
        mock_obj = {"key1": "value1", "key2": "value2"}

        def accessor(x):
            return x

        def pure_impl(x):
            return f"Pure({x})"

        proxy_ctx = DynamicProxyContextImpl(
            accessor=accessor, pure_impl=pure_impl, _alias_name="TestProxy"
        )

        result = proxy_ctx.getitem(mock_obj, "key1")

        assert isinstance(result, DelegatedVar)
        assert result.value == "Pure(value1)"

    def test_eval(self):
        """Test eval method."""
        mock_obj = Mock()
        mock_obj.data = "test_data"

        def accessor(x):
            return x.data

        def pure_impl(x):
            return x

        proxy_ctx = DynamicProxyContextImpl(
            accessor=accessor, pure_impl=pure_impl, _alias_name="TestProxy"
        )

        result = proxy_ctx.eval(mock_obj)

        assert result == "test_data"

    def test_alias_name(self):
        """Test alias_name method."""
        proxy_ctx = DynamicProxyContextImpl(
            accessor=lambda x: x, pure_impl=lambda x: x, _alias_name="MyCustomProxy"
        )

        assert proxy_ctx.alias_name() == "MyCustomProxy"

    def test_iter(self):
        """Test iter method."""
        mock_iterable = [1, 2, 3]

        def accessor(x):
            return x

        def pure_impl(x):
            return f"Pure({x})"

        proxy_ctx = DynamicProxyContextImpl(
            accessor=accessor, pure_impl=pure_impl, _alias_name="TestProxy"
        )

        result = proxy_ctx.iter(mock_iterable)

        assert isinstance(result, DynamicProxyIterator)
        assert result.cxt is proxy_ctx

    def test_dir(self):
        """Test dir method."""

        class TestClass:
            def __init__(self):
                self.attr1 = 1
                self.attr2 = 2

            def method1(self):
                pass

        mock_obj = TestClass()

        proxy_ctx = DynamicProxyContextImpl(
            accessor=lambda x: x, pure_impl=lambda x: x, _alias_name="TestProxy"
        )

        result = proxy_ctx.dir(mock_obj)

        assert "attr1" in result
        assert "attr2" in result
        assert "method1" in result

    def test_map(self):
        """Test map method."""
        mock_obj = 10

        def accessor(x):
            return x

        def pure_impl(x):
            return f"Pure({x})"

        proxy_ctx = DynamicProxyContextImpl(
            accessor=accessor, pure_impl=pure_impl, _alias_name="TestProxy"
        )

        def mapper(x):
            return x * 2

        result = proxy_ctx.map(mock_obj, mapper)

        assert isinstance(result, DelegatedVar)
        assert result.value == "Pure(20)"


class TestDynamicProxyIterator:
    """Test the DynamicProxyIterator class."""

    def test_dynamic_proxy_iterator_is_dataclass(self):
        """Test that DynamicProxyIterator is a dataclass."""
        assert is_dataclass(DynamicProxyIterator)

    def test_dynamic_proxy_iterator_creation(self):
        """Test creating DynamicProxyIterator instance."""
        mock_iter = iter([1, 2, 3])
        mock_ctx = Mock(spec=DynamicProxyContextImpl)

        proxy_iter = DynamicProxyIterator(src=mock_iter, cxt=mock_ctx)

        assert proxy_iter.src is mock_iter
        assert proxy_iter.cxt is mock_ctx

    def test_iter_returns_self(self):
        """Test __iter__ returns self."""
        mock_iter = iter([1, 2, 3])
        mock_ctx = Mock(spec=DynamicProxyContextImpl)

        proxy_iter = DynamicProxyIterator(src=mock_iter, cxt=mock_ctx)

        assert iter(proxy_iter) is proxy_iter

    def test_next(self):
        """Test __next__ method."""
        source_list = [1, 2, 3]
        mock_iter = iter(source_list)

        # Create mock context that returns DelegatedVar
        mock_ctx = Mock(spec=DynamicProxyContextImpl)
        mock_ctx.pure.side_effect = lambda x: DelegatedVar(f"Pure({x})", mock_ctx)

        proxy_iter = DynamicProxyIterator(src=mock_iter, cxt=mock_ctx)

        # Test iteration
        result1 = next(proxy_iter)
        assert isinstance(result1, DelegatedVar)
        assert result1.value == "Pure(1)"

        result2 = next(proxy_iter)
        assert isinstance(result2, DelegatedVar)
        assert result2.value == "Pure(2)"

        result3 = next(proxy_iter)
        assert isinstance(result3, DelegatedVar)
        assert result3.value == "Pure(3)"

        # Should raise StopIteration when exhausted
        with pytest.raises(StopIteration):
            next(proxy_iter)

    def test_full_iteration(self):
        """Test iterating through the entire sequence."""
        source_list = ["a", "b", "c"]
        mock_iter = iter(source_list)

        mock_ctx = Mock(spec=DynamicProxyContextImpl)
        mock_ctx.pure.side_effect = lambda x: DelegatedVar(f"Pure({x})", mock_ctx)

        proxy_iter = DynamicProxyIterator(src=mock_iter, cxt=mock_ctx)

        results = list(proxy_iter)

        assert len(results) == 3
        assert all(isinstance(r, DelegatedVar) for r in results)
        assert [r.value for r in results] == ["Pure(a)", "Pure(b)", "Pure(c)"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
