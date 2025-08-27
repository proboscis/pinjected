"""Tests for pinjected/di/proxiable.py module to improve coverage."""

import pytest
import pickle

from pinjected.di.proxiable import DelegatedVar, IProxyContext


class MockProxyContext(IProxyContext):
    """Mock implementation of IProxyContext for testing."""

    def getattr(self, tgt, name):
        return f"getattr_{name}"

    def call(self, tgt, *args, **kwargs):
        return f"call_result"

    def pure(self, tgt):
        return DelegatedVar(tgt, self)

    def getitem(self, tgt, key):
        return f"getitem_{key}"

    def eval(self, tgt):
        return f"eval_{tgt}"

    def alias_name(self):
        return "MockProxy"

    def iter(self, tgt):
        return iter([1, 2, 3])

    def dir(self, tgt):
        return ["attr1", "attr2"]

    def biop_impl(self, op, tgt, other):
        return f"biop_{op}_{tgt}_{other}"

    def unary_impl(self, op, tgt):
        return f"unary_{op}_{tgt}"


class TestDelegatedVarUncoveredMethods:
    """Test uncovered methods in DelegatedVar."""

    def test_iter_method(self):
        """Test __iter__ method (line 93)."""
        ctx = MockProxyContext()
        var = DelegatedVar("test_value", ctx)

        # Test iteration
        result = list(var)
        assert result == [1, 2, 3]

    def test_getstate_setstate(self):
        """Test __getstate__ and __setstate__ methods (lines 96, 99)."""
        ctx = MockProxyContext()
        var = DelegatedVar("test_value", ctx)

        # Test __getstate__
        state = var.__getstate__()
        assert state == ("test_value", ctx)

        # Test __setstate__
        new_var = DelegatedVar(None, None)
        new_var.__setstate__(("new_value", ctx))
        assert new_var.__value__ == "new_value"
        assert new_var.__cxt__ is ctx

    def test_pickle_support(self):
        """Test that DelegatedVar can be pickled and unpickled."""
        ctx = MockProxyContext()
        var = DelegatedVar("test_value", ctx)

        # Pickle and unpickle
        pickled = pickle.dumps(var)
        unpickled = pickle.loads(pickled)

        assert unpickled.__value__ == "test_value"
        assert isinstance(unpickled.__cxt__, MockProxyContext)

    def test_mod_operator(self):
        """Test __mod__ operator (line 114)."""
        ctx = MockProxyContext()
        var = DelegatedVar(10, ctx)

        result = var % 3
        assert result == "biop_%_10_3"

    def test_invert_operator(self):
        """Test __invert__ operator (line 120)."""
        ctx = MockProxyContext()
        var = DelegatedVar(5, ctx)

        result = ~var
        assert result == "unary_~_5"

    def test_await_method(self):
        """Test await__ method (line 123)."""
        ctx = MockProxyContext()
        var = DelegatedVar("async_value", ctx)

        result = var.await__()
        assert result == "unary_await_async_value"


class TestIProxyContextDefaultImplementations:
    """Test default implementations in IProxyContext."""

    def test_biop_impl_not_implemented(self):
        """Test that biop_impl raises NotImplementedError by default."""

        # Create a minimal implementation that doesn't override biop_impl
        class MinimalProxyContext(IProxyContext):
            def getattr(self, tgt, name):
                pass

            def call(self, tgt, *args, **kwargs):
                pass

            def pure(self, tgt):
                pass

            def getitem(self, tgt, key):
                pass

            def eval(self, tgt):
                pass

            def alias_name(self):
                pass

            def iter(self, tgt):
                pass

            def dir(self, tgt):
                pass

        ctx = MinimalProxyContext()
        with pytest.raises(NotImplementedError):
            ctx.biop_impl("+", "value", "other")

    def test_unary_impl_not_implemented(self):
        """Test that unary_impl raises NotImplementedError by default."""

        # Create a minimal implementation that doesn't override unary_impl
        class MinimalProxyContext(IProxyContext):
            def getattr(self, tgt, name):
                pass

            def call(self, tgt, *args, **kwargs):
                pass

            def pure(self, tgt):
                pass

            def getitem(self, tgt, key):
                pass

            def eval(self, tgt):
                pass

            def alias_name(self):
                pass

            def iter(self, tgt):
                pass

            def dir(self, tgt):
                pass

        ctx = MinimalProxyContext()
        with pytest.raises(NotImplementedError):
            ctx.unary_impl("-", "value")

    def test_magic_method_impl_returns_not_implemented(self):
        """Test that magic_method_impl returns NotImplemented by default."""

        # Create a minimal implementation
        class MinimalProxyContext(IProxyContext):
            def getattr(self, tgt, name):
                pass

            def call(self, tgt, *args, **kwargs):
                pass

            def pure(self, tgt):
                pass

            def getitem(self, tgt, key):
                pass

            def eval(self, tgt):
                pass

            def alias_name(self):
                pass

            def iter(self, tgt):
                pass

            def dir(self, tgt):
                pass

        ctx = MinimalProxyContext()
        result = ctx.magic_method_impl("__len__", "value")
        assert result is NotImplemented


class TestDelegatedVarAdditionalOperators:
    """Test additional operators and edge cases."""

    def test_multiple_operators_chain(self):
        """Test chaining multiple operators."""
        ctx = MockProxyContext()
        var = DelegatedVar(10, ctx)

        # Test multiple operations
        result1 = var + 5
        assert result1 == "biop_+_10_5"

        result2 = var * 2
        assert result2 == "biop_*_10_2"

        result3 = var / 3
        assert result3 == "biop_/_10_3"

        result4 = var == 10
        assert result4 == "biop_==_10_10"

    def test_delegated_var_with_complex_value(self):
        """Test DelegatedVar with complex object as value."""
        ctx = MockProxyContext()
        complex_obj = {"key": "value", "list": [1, 2, 3]}
        var = DelegatedVar(complex_obj, ctx)

        # Test operations
        result = var % "test"
        assert result == f"biop_%_{complex_obj}_test"

        # Test iteration
        iter_result = list(var)
        assert iter_result == [1, 2, 3]


class TestDelegatedVarCoreMethods:
    """Test core methods that were not covered."""

    def test_getattr_blocks_dunder_attributes(self):
        """Test that __getattr__ blocks dunder attributes (lines 66-76)."""
        ctx = MockProxyContext()
        var = DelegatedVar("value", ctx)

        # Test blocking dunder attributes
        with pytest.raises(AttributeError, match="blocks access to '__test__'"):
            var.__test__

        # Test blocking signature attribute
        with pytest.raises(AttributeError, match="blocks access to 'signature'"):
            var.signature

        # Test blocking func attribute
        with pytest.raises(AttributeError, match="blocks access to 'func'"):
            var.func

        # Test blocking im_func attribute
        with pytest.raises(AttributeError, match="blocks access to 'im_func'"):
            var.im_func

    def test_getattr_allows_normal_attributes(self):
        """Test that __getattr__ allows normal attributes."""
        ctx = MockProxyContext()
        var = DelegatedVar("value", ctx)

        # Normal attributes should work
        result = var.normal_attr
        assert result == "getattr_normal_attr"

    def test_call_method(self):
        """Test __call__ method (lines 79-80)."""
        ctx = MockProxyContext()
        var = DelegatedVar("callable_value", ctx)

        result = var(1, 2, key="value")
        assert result == "call_result"

    def test_getitem_method(self):
        """Test __getitem__ method (line 83)."""
        ctx = MockProxyContext()
        var = DelegatedVar({"key": "value"}, ctx)

        result = var["key"]
        assert result == "getitem_key"

    def test_eval_method(self):
        """Test eval method (line 87)."""
        ctx = MockProxyContext()
        var = DelegatedVar("test_value", ctx)

        result = var.eval()
        assert result == "eval_test_value"

    def test_str_method(self):
        """Test __str__ method (line 90)."""
        ctx = MockProxyContext()
        var = DelegatedVar("test_value", ctx)

        result = str(var)
        # Check that it contains the expected parts
        assert "MockProxy(test_value," in result
        assert "MockProxyContext object at" in result

    def test_hash_method(self):
        """Test __hash__ method (line 102)."""
        ctx = MockProxyContext()
        var1 = DelegatedVar("value", ctx)
        var2 = DelegatedVar("value", ctx)
        var3 = DelegatedVar("other", ctx)

        # Same value and context should have same hash
        assert hash(var1) == hash(var2)

        # Different value should have different hash
        assert hash(var1) != hash(var3)

        # Can be used in sets/dicts
        test_set = {var1, var2, var3}
        assert len(test_set) == 2  # var1 and var2 are considered equal


class TestDelegatedVarEdgeCases:
    """Test edge cases and special scenarios."""

    def test_nested_delegated_vars(self):
        """Test DelegatedVar containing another DelegatedVar."""
        ctx = MockProxyContext()
        inner_var = DelegatedVar("inner", ctx)
        outer_var = DelegatedVar(inner_var, ctx)

        # Should be able to evaluate nested
        result = outer_var.eval()
        assert result == f"eval_{inner_var}"

    def test_delegated_var_with_none_value(self):
        """Test DelegatedVar with None as value."""
        ctx = MockProxyContext()
        var = DelegatedVar(None, ctx)

        # All operations should still work with None
        str_result = str(var)
        assert "MockProxy(None," in str_result

        hash_result = hash(var)
        assert isinstance(hash_result, int)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
