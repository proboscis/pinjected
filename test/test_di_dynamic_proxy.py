"""Tests for di/dynamic_proxy.py module."""

import pytest
from dataclasses import is_dataclass
from unittest.mock import Mock, patch

from pinjected.di.dynamic_proxy import DynamicProxyContextImpl, DynamicProxyIterator
from pinjected.di.proxiable import DelegatedVar


class TestDynamicProxyContextImpl:
    """Test DynamicProxyContextImpl class."""

    def test_is_dataclass(self):
        """Test that DynamicProxyContextImpl is a dataclass."""
        assert is_dataclass(DynamicProxyContextImpl)

    def test_creation(self):
        """Test DynamicProxyContextImpl creation."""
        accessor = Mock()
        pure_impl = Mock()
        alias = "test_alias"

        context = DynamicProxyContextImpl(
            accessor=accessor, pure_impl=pure_impl, _alias_name=alias
        )

        assert context.accessor is accessor
        assert context.pure_impl is pure_impl
        assert context._alias_name == alias

    def test_getattr(self):
        """Test getattr method."""
        # Setup
        target_obj = Mock()
        attr_value = "attr_value"
        wrapped_value = "wrapped_attr"

        accessor = Mock(return_value=Mock(**{"test_attr": attr_value}))
        pure_impl = Mock(return_value=wrapped_value)

        context = DynamicProxyContextImpl(
            accessor=accessor, pure_impl=pure_impl, _alias_name="test"
        )

        # Test
        result = context.getattr(target_obj, "test_attr")

        # Verify
        assert isinstance(result, DelegatedVar)
        assert (
            result.__value__ == wrapped_value
        )  # Use internal attribute to avoid equality check
        assert result.__cxt__ is context
        accessor.assert_called_once_with(target_obj)
        pure_impl.assert_called_once_with(attr_value)

    def test_call(self):
        """Test call method."""
        # Setup
        target_obj = Mock()
        call_result = "call_result"
        wrapped_result = "wrapped_result"

        callable_obj = Mock(return_value=call_result)
        accessor = Mock(return_value=callable_obj)
        pure_impl = Mock(return_value=wrapped_result)

        context = DynamicProxyContextImpl(
            accessor=accessor, pure_impl=pure_impl, _alias_name="test"
        )

        # Test
        result = context.call(target_obj, "arg1", "arg2", key="value")

        # Verify
        assert isinstance(result, DelegatedVar)
        assert result.__value__ == wrapped_result
        accessor.assert_called_once_with(target_obj)
        callable_obj.assert_called_once_with("arg1", "arg2", key="value")
        pure_impl.assert_called_once_with(call_result)

    def test_pure(self):
        """Test pure method."""
        # Setup
        target_value = "target"
        wrapped_value = "wrapped"

        accessor = Mock()
        pure_impl = Mock(return_value=wrapped_value)

        context = DynamicProxyContextImpl(
            accessor=accessor, pure_impl=pure_impl, _alias_name="test"
        )

        # Test
        result = context.pure(target_value)

        # Verify
        assert isinstance(result, DelegatedVar)
        assert result.__value__ == wrapped_value
        assert result.__cxt__ is context
        pure_impl.assert_called_once_with(target_value)

    def test_getitem(self):
        """Test getitem method."""
        # Setup
        target_obj = Mock()
        item_value = "item_value"
        wrapped_value = "wrapped_item"

        indexable_obj = {"key": item_value}
        accessor = Mock(return_value=indexable_obj)
        pure_impl = Mock(return_value=wrapped_value)

        context = DynamicProxyContextImpl(
            accessor=accessor, pure_impl=pure_impl, _alias_name="test"
        )

        # Test
        result = context.getitem(target_obj, "key")

        # Verify
        assert isinstance(result, DelegatedVar)
        assert result.__value__ == wrapped_value
        accessor.assert_called_once_with(target_obj)
        pure_impl.assert_called_once_with(item_value)

    def test_eval(self):
        """Test eval method."""
        # Setup
        target_obj = Mock()
        eval_result = "eval_result"

        accessor = Mock(return_value=eval_result)
        pure_impl = Mock()

        context = DynamicProxyContextImpl(
            accessor=accessor, pure_impl=pure_impl, _alias_name="test"
        )

        # Test
        result = context.eval(target_obj)

        # Verify
        assert result == eval_result
        accessor.assert_called_once_with(target_obj)

    def test_alias_name(self):
        """Test alias_name method."""
        # Setup
        alias = "test_alias"
        context = DynamicProxyContextImpl(
            accessor=Mock(), pure_impl=Mock(), _alias_name=alias
        )

        # Test
        result = context.alias_name()

        # Verify
        assert result == alias

    def test_iter(self):
        """Test iter method."""
        # Setup
        target_obj = Mock()
        iterable_obj = [1, 2, 3]

        accessor = Mock(return_value=iterable_obj)
        pure_impl = Mock()

        context = DynamicProxyContextImpl(
            accessor=accessor, pure_impl=pure_impl, _alias_name="test"
        )

        # Test
        result = context.iter(target_obj)

        # Verify
        assert isinstance(result, DynamicProxyIterator)
        assert result.cxt is context
        accessor.assert_called_once_with(target_obj)

    def test_dir(self):
        """Test dir method."""
        # Setup
        target_obj = Mock()
        dir_result = ["attr1", "attr2", "method1"]

        obj_with_attrs = Mock()
        accessor = Mock(return_value=obj_with_attrs)
        pure_impl = Mock()

        # Mock dir() to return our result
        with patch("pinjected.di.dynamic_proxy.dir", return_value=dir_result):
            context = DynamicProxyContextImpl(
                accessor=accessor, pure_impl=pure_impl, _alias_name="test"
            )

            # Test
            result = context.dir(target_obj)

            # Verify
            assert result == dir_result
            accessor.assert_called_once_with(target_obj)

    def test_map(self):
        """Test map method."""
        # Setup
        target_obj = Mock()
        accessed_value = "accessed"
        mapped_value = "mapped"
        wrapped_value = "wrapped"

        accessor = Mock(return_value=accessed_value)
        pure_impl = Mock(return_value=wrapped_value)
        map_func = Mock(return_value=mapped_value)

        context = DynamicProxyContextImpl(
            accessor=accessor, pure_impl=pure_impl, _alias_name="test"
        )

        # Test
        result = context.map(target_obj, map_func)

        # Verify
        assert isinstance(result, DelegatedVar)
        assert result.__value__ == wrapped_value
        accessor.assert_called_once_with(target_obj)
        map_func.assert_called_once_with(accessed_value)
        pure_impl.assert_called_once_with(mapped_value)


class TestDynamicProxyIterator:
    """Test DynamicProxyIterator class."""

    def test_is_dataclass(self):
        """Test that DynamicProxyIterator is a dataclass."""
        assert is_dataclass(DynamicProxyIterator)

    def test_creation(self):
        """Test DynamicProxyIterator creation."""
        src_iter = iter([1, 2, 3])
        context = Mock(spec=DynamicProxyContextImpl)

        iterator = DynamicProxyIterator(src=src_iter, cxt=context)

        assert iterator.src is src_iter
        assert iterator.cxt is context

    def test_iter(self):
        """Test __iter__ method."""
        src_iter = iter([1, 2, 3])
        context = Mock(spec=DynamicProxyContextImpl)

        iterator = DynamicProxyIterator(src=src_iter, cxt=context)

        # Test
        result = iter(iterator)

        # Verify
        assert result is iterator

    def test_next(self):
        """Test __next__ method."""
        # Setup
        values = [1, 2, 3]
        wrapped_values = ["wrapped1", "wrapped2", "wrapped3"]

        src_iter = iter(values)
        context = Mock(spec=DynamicProxyContextImpl)

        # Mock pure to return DelegatedVar with wrapped values
        def mock_pure(value):
            idx = values.index(value)
            return DelegatedVar(wrapped_values[idx], context)

        context.pure = Mock(side_effect=mock_pure)

        iterator = DynamicProxyIterator(src=src_iter, cxt=context)

        # Test
        result1 = next(iterator)
        result2 = next(iterator)
        result3 = next(iterator)

        # Verify
        assert isinstance(result1, DelegatedVar)
        assert result1.__value__ == "wrapped1"
        assert isinstance(result2, DelegatedVar)
        assert result2.__value__ == "wrapped2"
        assert isinstance(result3, DelegatedVar)
        assert result3.__value__ == "wrapped3"

        # Should raise StopIteration when exhausted
        with pytest.raises(StopIteration):
            next(iterator)

    def test_iteration_in_loop(self):
        """Test iteration in a for loop."""
        # Setup
        values = [10, 20, 30]

        src_iter = iter(values)
        context = Mock(spec=DynamicProxyContextImpl)

        # Mock pure to return DelegatedVar
        def mock_pure(value):
            return DelegatedVar(f"wrapped_{value}", context)

        context.pure = Mock(side_effect=mock_pure)

        iterator = DynamicProxyIterator(src=src_iter, cxt=context)

        # Test
        results = []
        for item in iterator:
            results.append(item)

        # Verify
        assert len(results) == 3
        assert all(isinstance(r, DelegatedVar) for r in results)
        assert [r.__value__ for r in results] == [
            "wrapped_10",
            "wrapped_20",
            "wrapped_30",
        ]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
