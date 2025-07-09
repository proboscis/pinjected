"""Simple tests for di/app_designed.py module to improve coverage."""

import pytest
from unittest.mock import Mock, patch
from dataclasses import is_dataclass

from pinjected.di.app_designed import (
    ApplicativeDesignedImpl,
    EvaledDesigned,
    reduce_designed_expr,
    eval_designed,
    designed_proxy,
    ApplicativeDesigned,
    DesignedEvalContext,
)
from pinjected import Design, Designed, Injected, design
from pinjected.di.designed import PureDesigned
from pinjected.di.injected import InjectedPure
from pinjected.di.expr_util import Object, BiOp


class TestApplicativeDesignedImpl:
    """Test the ApplicativeDesignedImpl class."""

    def test_applicative_designed_impl_map(self):
        """Test map method."""
        app = ApplicativeDesignedImpl()

        # Create a mock Designed
        mock_designed = Mock(spec=Designed)
        mock_designed.map.return_value = "mapped_result"

        def mapper(x):
            return x * 2

        result = app.map(mock_designed, mapper)

        mock_designed.map.assert_called_once_with(mapper)
        assert result == "mapped_result"

    def test_applicative_designed_impl_zip(self):
        """Test zip method."""
        app = ApplicativeDesignedImpl()

        # Create mock Designed instances
        designed1 = Mock(spec=Designed)
        designed2 = Mock(spec=Designed)
        designed3 = Mock(spec=Designed)

        with patch.object(Designed, "zip", return_value="zipped_result") as mock_zip:
            result = app.zip(designed1, designed2, designed3)

            mock_zip.assert_called_once_with(designed1, designed2, designed3)
            assert result == "zipped_result"

    def test_applicative_designed_impl_is_instance(self):
        """Test is_instance method."""
        app = ApplicativeDesignedImpl()

        # Test with mocked Designed instance
        from unittest.mock import Mock

        designed = Mock(spec=Designed)
        assert app.is_instance(designed) is True

        # Test with non-Designed instance
        assert app.is_instance("not_designed") is False
        assert app.is_instance(42) is False


class TestReduceDesignedExpr:
    """Test the reduce_designed_expr function."""

    def test_reduce_designed_expr_with_pure_designed(self):
        """Test reduce_designed_expr with PureDesigned in Object."""
        # Create a PureDesigned wrapped in Object
        test_design = design(test="value")
        pure_designed = PureDesigned(test_design, InjectedPure("test_value"))
        expr = Object(pure_designed)

        result = reduce_designed_expr(expr)

        assert "Object(test_value with" in result
        assert "Design" in result

    def test_reduce_designed_expr_no_match(self):
        """Test reduce_designed_expr with non-matching expression."""
        # Test with expressions that don't match the pattern
        expr1 = Object("simple_string")
        expr2 = Object(42)  # Use Object instead of Const
        expr3 = BiOp("+", Object("a"), Object("b"))

        # Should return None (no match)
        assert reduce_designed_expr(expr1) is None
        assert reduce_designed_expr(expr2) is None
        assert reduce_designed_expr(expr3) is None


class TestEvaledDesigned:
    """Test the EvaledDesigned class."""

    def test_evaled_designed_is_dataclass(self):
        """Test that EvaledDesigned is a dataclass."""
        assert is_dataclass(EvaledDesigned)

    def test_evaled_designed_creation(self):
        """Test creating EvaledDesigned instance."""
        mock_designed = Mock(spec=Designed)
        mock_ast = Object("test")

        evaled = EvaledDesigned(value=mock_designed, ast=mock_ast)

        assert evaled.value is mock_designed
        assert evaled.ast is mock_ast

    def test_evaled_designed_design_property(self):
        """Test design property delegates to value."""
        mock_designed = Mock(spec=Designed)
        mock_design = Mock(spec=Design)
        mock_designed.design = mock_design

        evaled = EvaledDesigned(value=mock_designed, ast=Object("test"))

        assert evaled.design is mock_design

    def test_evaled_designed_internal_injected_property(self):
        """Test internal_injected property delegates to value."""
        mock_designed = Mock(spec=Designed)
        mock_injected = Mock(spec=Injected)
        mock_designed.internal_injected = mock_injected

        evaled = EvaledDesigned(value=mock_designed, ast=Object("test"))

        assert evaled.internal_injected is mock_injected

    def test_evaled_designed_str(self):
        """Test string representation."""
        mock_designed = Mock(spec=Designed)
        mock_designed.__str__ = Mock(return_value="MockDesigned")

        evaled = EvaledDesigned(value=mock_designed, ast=Object("test"))
        str_repr = str(evaled)

        assert "EvaledDesigned" in str_repr
        assert "value=" in str_repr
        assert "ast=" in str_repr


class TestEvalDesigned:
    """Test the eval_designed function."""

    @patch("pinjected.di.app_designed.eval_applicative")
    def test_eval_designed(self, mock_eval_applicative):
        """Test eval_designed function."""
        # Setup
        mock_expr = Object("test")
        mock_result = Mock(spec=Designed)
        mock_eval_applicative.return_value = mock_result

        # Call function
        result = eval_designed(mock_expr)

        # Verify
        mock_eval_applicative.assert_called_once_with(mock_expr, ApplicativeDesigned)
        assert isinstance(result, EvaledDesigned)
        assert result.value is mock_result
        assert result.ast is mock_expr


class TestDesignedProxy:
    """Test the designed_proxy function."""

    @patch("pinjected.di.app_designed.ast_proxy")
    def test_designed_proxy(self, mock_ast_proxy):
        """Test designed_proxy function."""
        mock_designed = Mock(spec=Designed)
        mock_proxy = Mock()
        mock_ast_proxy.return_value = mock_proxy

        result = designed_proxy(mock_designed)

        mock_ast_proxy.assert_called_once_with(mock_designed, DesignedEvalContext)
        assert result is mock_proxy


class TestModuleGlobals:
    """Test module-level globals."""

    def test_applicative_designed_is_instance(self):
        """Test ApplicativeDesigned is an instance of ApplicativeDesignedImpl."""
        assert isinstance(ApplicativeDesigned, ApplicativeDesignedImpl)

    def test_designed_eval_context_has_alias(self):
        """Test DesignedEvalContext has correct alias."""
        assert hasattr(DesignedEvalContext, "_alias_name")
        assert DesignedEvalContext._alias_name == "DesignedProxy"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
