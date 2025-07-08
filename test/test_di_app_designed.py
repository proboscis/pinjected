"""Tests for di/app_designed.py module."""

import pytest
from unittest.mock import Mock
from pinjected import Design, Designed, Injected
from pinjected.di.app_designed import (
    ApplicativeDesignedImpl,
    reduce_designed_expr,
    EvaledDesigned,
    eval_designed,
    designed_proxy,
    ApplicativeDesigned,
    DesignedEvalContext,
)
from pinjected.di.designed import PureDesigned
from pinjected.di.expr_util import Expr, Object
from pinjected.di.injected import InjectedPure
from pinjected.di.proxiable import DelegatedVar


class TestApplicativeDesignedImpl:
    """Tests for ApplicativeDesignedImpl class."""

    def test_map(self):
        """Test map method."""
        impl = ApplicativeDesignedImpl()

        # Create a mock Designed object
        designed = Mock(spec=Designed)
        designed.map = Mock(return_value="mapped_result")

        # Test mapping
        def f(x):
            return x * 2

        result = impl.map(designed, f)

        designed.map.assert_called_once_with(f)
        assert result == "mapped_result"

    def test_zip(self):
        """Test zip method."""
        impl = ApplicativeDesignedImpl()

        # Create mock Designed objects
        designed1 = Mock(spec=Designed)
        designed2 = Mock(spec=Designed)
        designed3 = Mock(spec=Designed)

        # Mock Designed.zip
        Designed.zip = Mock(return_value="zipped_result")

        # Test zipping
        result = impl.zip(designed1, designed2, designed3)

        Designed.zip.assert_called_once_with(designed1, designed2, designed3)
        assert result == "zipped_result"

    def test_pure(self):
        """Test pure method."""
        impl = ApplicativeDesignedImpl()

        # Mock Injected.pure and Designed.bind
        Injected.pure = Mock(return_value="pure_injected")
        Designed.bind = Mock(return_value="designed_result")

        # Test pure
        value = 42
        result = impl.pure(value)

        Injected.pure.assert_called_once_with(value)
        Designed.bind.assert_called_once_with("pure_injected")
        assert result == "designed_result"

    def test_is_instance_true(self):
        """Test is_instance with Designed object."""
        impl = ApplicativeDesignedImpl()

        # Create a mock Designed object
        designed = Mock(spec=Designed)

        result = impl.is_instance(designed)
        assert result is True

    def test_is_instance_false(self):
        """Test is_instance with non-Designed object."""
        impl = ApplicativeDesignedImpl()

        result = impl.is_instance("not_designed")
        assert result is False


def test_reduce_designed_expr():
    """Test reduce_designed_expr function."""
    # Create mock objects
    design = Mock(spec=Design)
    value = "test_value"

    # Create PureDesigned with InjectedPure
    injected_pure = InjectedPure(value)
    pure_designed = PureDesigned(design, injected_pure)

    # Create Object expr
    expr = Object(pure_designed)

    # Test reduction
    result = reduce_designed_expr(expr)
    expected = f"Object({value!s} with {design})"
    assert result == expected


def test_reduce_designed_expr_no_match():
    """Test reduce_designed_expr with non-matching expression."""
    # Create a different type of expression
    expr = Object("not_pure_designed")

    # Should return None for non-matching expressions
    result = reduce_designed_expr(expr)
    assert result is None


class TestEvaledDesigned:
    """Tests for EvaledDesigned class."""

    def test_creation(self):
        """Test EvaledDesigned creation."""
        # Create mocks
        value = Mock(spec=Designed)
        ast = Mock(spec=Expr)

        # Create EvaledDesigned
        evaled = EvaledDesigned(value=value, ast=ast)

        assert evaled.value is value
        assert evaled.ast is ast

    def test_design_property(self):
        """Test design property."""
        # Create mocks
        design = Mock(spec=Design)
        value = Mock(spec=Designed)
        value.design = design
        ast = Mock(spec=Expr)

        # Create EvaledDesigned
        evaled = EvaledDesigned(value=value, ast=ast)

        assert evaled.design is design

    def test_internal_injected_property(self):
        """Test internal_injected property."""
        # Create mocks
        injected = Mock(spec=Injected)
        value = Mock(spec=Designed)
        value.internal_injected = injected
        ast = Mock(spec=Expr)

        # Create EvaledDesigned
        evaled = EvaledDesigned(value=value, ast=ast)

        assert evaled.internal_injected is injected

    def test_str_representation(self):
        """Test string representation."""
        # Create mocks
        value = Mock(spec=Designed)
        value.__str__ = Mock(return_value="MockDesigned")

        # Create a simple Object expression for testing
        from pinjected.di.expr_util import Object

        ast = Object("test_value")

        # Create EvaledDesigned
        evaled = EvaledDesigned(value=value, ast=ast)

        result = str(evaled)
        # The ast will be shown as "test_value" with quotes due to Object expression containing a string
        expected = 'EvaledDesigned(value=MockDesigned,ast="test_value")'
        assert result == expected


def test_eval_designed():
    """Test eval_designed function."""
    # Create a simple Object expression
    from pinjected.di.expr_util import Object

    # Create a mock Designed object
    designed = Mock(spec=Designed)
    designed.design = Mock(spec=Design)
    designed.internal_injected = Mock(spec=Injected)

    # Since ApplicativeDesigned.is_instance checks for Designed type,
    # we need to ensure our mock is recognized as Designed
    expr = Object(designed)

    # Test eval_designed
    result = eval_designed(expr)

    # Verify it returns EvaledDesigned
    assert isinstance(result, EvaledDesigned)
    assert result.ast is expr
    # The value should be the designed object itself (passed through pure/eval)
    assert isinstance(result.value, (Mock, Designed))


def test_designed_proxy():
    """Test designed_proxy function."""
    # Create mock designed
    designed = Mock(spec=Designed)

    # Test designed_proxy
    result = designed_proxy(designed)

    # Verify it returns a DelegatedVar
    assert isinstance(result, DelegatedVar)
    assert result.__value__ is designed
    assert result.__cxt__ is DesignedEvalContext


def test_applicative_designed_singleton():
    """Test that ApplicativeDesigned is a singleton instance."""
    assert isinstance(ApplicativeDesigned, ApplicativeDesignedImpl)


def test_designed_eval_context():
    """Test DesignedEvalContext is properly configured."""
    # DesignedEvalContext should be an AstProxyContextImpl
    from pinjected.di.static_proxy import AstProxyContextImpl

    assert isinstance(DesignedEvalContext, AstProxyContextImpl)

    # Check it's configured with eval_designed
    # Note: We can't directly check the function reference due to how it's created,
    # but we can verify it has the expected alias
    assert hasattr(DesignedEvalContext, "_alias_name")
    assert DesignedEvalContext._alias_name == "DesignedProxy"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
