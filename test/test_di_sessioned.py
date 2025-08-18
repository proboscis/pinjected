"""Tests for pinjected/di/sessioned.py module."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from pinjected.di.sessioned import (
    Sessioned,
    ApplicativeSesionedImpl,
    eval_sessioned,
    sessioned_ast_context,
)
from pinjected.di.designed import Designed
from pinjected.di.injected import Injected
from pinjected.di.expr_util import Expr


class TestSessioned:
    """Tests for Sessioned class."""

    def test_sessioned_creation(self):
        """Test creating a Sessioned instance."""
        mock_parent = Mock()
        mock_designed = Mock(spec=Designed)

        sessioned = Sessioned(parent=mock_parent, designed=mock_designed)

        assert sessioned.parent == mock_parent
        assert sessioned.designed == mock_designed

    def test_sessioned_map(self):
        """Test map method of Sessioned."""
        mock_parent = Mock()
        mock_designed = Mock(spec=Designed)
        mock_designed.map = Mock(return_value="mapped_designed")

        sessioned = Sessioned(parent=mock_parent, designed=mock_designed)

        def f(x):
            return x * 2

        result = sessioned.map(f)

        assert isinstance(result, Sessioned)
        assert result.parent == mock_parent
        assert result.designed == "mapped_designed"
        mock_designed.map.assert_called_once_with(f)

    def test_sessioned_zip(self):
        """Test zip method of Sessioned."""
        mock_parent = Mock()

        # Create designed mocks
        designed1 = Mock(spec=Designed)
        designed2 = Mock(spec=Designed)
        designed3 = Mock(spec=Designed)

        # Create sessioned instances
        sessioned1 = Sessioned(parent=mock_parent, designed=designed1)
        sessioned2 = Sessioned(parent=mock_parent, designed=designed2)
        sessioned3 = Sessioned(parent=mock_parent, designed=designed3)

        # Mock Designed.zip
        with patch.object(Designed, "zip", return_value="zipped_designed") as mock_zip:
            result = sessioned1.zip(sessioned2, sessioned3)

            assert isinstance(result, Sessioned)
            assert result.parent == mock_parent
            assert result.designed == "zipped_designed"
            mock_zip.assert_called_once_with(designed1, designed2, designed3)

    def test_sessioned_run(self):
        """Test run method of Sessioned."""
        mock_parent = MagicMock()
        mock_designed = Mock(spec=Designed)
        mock_parent.__getitem__.return_value = "run_result"

        sessioned = Sessioned(parent=mock_parent, designed=mock_designed)
        result = sessioned.run()

        assert result == "run_result"
        mock_parent.__getitem__.assert_called_once_with(mock_designed)

    def test_sessioned_run_sessioned(self):
        """Test run_sessioned method of Sessioned."""
        mock_parent = Mock()
        mock_parent.sessioned = Mock(return_value="sessioned_result")
        mock_designed = Mock(spec=Designed)

        sessioned = Sessioned(parent=mock_parent, designed=mock_designed)
        result = sessioned.run_sessioned()

        assert result == "sessioned_result"
        mock_parent.sessioned.assert_called_once_with(mock_designed)

    def test_sessioned_override(self):
        """Test override method of Sessioned."""
        mock_parent = Mock()
        mock_designed = Mock(spec=Designed)
        mock_designed.override = Mock(return_value="overridden_designed")
        mock_design = Mock()

        sessioned = Sessioned(parent=mock_parent, designed=mock_designed)
        result = sessioned.override(mock_design)

        assert isinstance(result, Sessioned)
        assert result.parent == mock_parent
        assert result.designed == "overridden_designed"
        mock_designed.override.assert_called_once_with(mock_design)

    def test_sessioned_proxy_property(self):
        """Test proxy property of Sessioned."""
        mock_parent = Mock()
        mock_parent.proxied = Mock(return_value="proxied_result")
        mock_designed = Mock(spec=Designed)

        sessioned = Sessioned(parent=mock_parent, designed=mock_designed)
        result = sessioned.proxy

        assert result == "proxied_result"
        mock_parent.proxied.assert_called_once_with(mock_designed)


class TestApplicativeSesionedImpl:
    """Tests for ApplicativeSesionedImpl class."""

    def test_applicative_sessioned_creation(self):
        """Test creating ApplicativeSesionedImpl instance."""
        mock_parent = Mock()
        app_impl = ApplicativeSesionedImpl(parent=mock_parent)

        assert app_impl.parent == mock_parent

    def test_applicative_sessioned_map(self):
        """Test map method."""
        mock_parent = Mock()
        app_impl = ApplicativeSesionedImpl(parent=mock_parent)

        mock_sessioned = Mock(spec=Sessioned)
        mock_sessioned.map = Mock(return_value="mapped_result")

        def f(x):
            return x + 1

        result = app_impl.map(mock_sessioned, f)

        assert result == "mapped_result"
        mock_sessioned.map.assert_called_once_with(f)

    def test_applicative_sessioned_zip_with_targets(self):
        """Test zip method with multiple targets."""
        mock_parent = Mock()
        app_impl = ApplicativeSesionedImpl(parent=mock_parent)

        # Create mock sessioneds
        sessioned1 = Mock(spec=Sessioned)
        sessioned2 = Mock(spec=Sessioned)
        sessioned3 = Mock(spec=Sessioned)

        sessioned1.zip = Mock(return_value="zipped_result")

        result = app_impl.zip(sessioned1, sessioned2, sessioned3)

        assert result == "zipped_result"
        sessioned1.zip.assert_called_once_with(sessioned2, sessioned3)

    def test_applicative_sessioned_zip_empty(self):
        """Test zip method with no targets."""
        mock_parent = Mock()
        app_impl = ApplicativeSesionedImpl(parent=mock_parent)

        # Mock the required classes
        with (
            patch.object(Designed, "bind") as mock_bind,
            patch.object(Injected, "pure") as mock_pure,
        ):
            mock_pure.return_value = "pure_unit"
            mock_bind.return_value = "bound_designed"

            result = app_impl.zip()

            assert isinstance(result, Sessioned)
            assert result.parent == mock_parent
            assert result.designed == "bound_designed"

            mock_pure.assert_called_once_with(())
            mock_bind.assert_called_once_with("pure_unit")

    def test_applicative_sessioned_pure(self):
        """Test pure method."""
        mock_parent = Mock()
        app_impl = ApplicativeSesionedImpl(parent=mock_parent)

        # Mock the required classes
        with (
            patch.object(Designed, "bind") as mock_bind,
            patch.object(Injected, "pure") as mock_pure,
        ):
            mock_pure.return_value = "pure_value"
            mock_bind.return_value = "bound_designed"

            result = app_impl.pure("test_item")

            assert isinstance(result, Sessioned)
            assert result.parent == mock_parent
            assert result.designed == "bound_designed"

            mock_pure.assert_called_once_with("test_item")
            mock_bind.assert_called_once_with("pure_value")

    def test_applicative_sessioned_is_instance(self):
        """Test is_instance method."""
        mock_parent = Mock()
        app_impl = ApplicativeSesionedImpl(parent=mock_parent)

        # Test with Sessioned instance
        sessioned = Sessioned(parent=mock_parent, designed=Mock())
        assert app_impl.is_instance(sessioned) is True

        # Test with non-Sessioned instance
        assert app_impl.is_instance("not_sessioned") is False
        assert app_impl.is_instance(123) is False


class TestEvalSessioned:
    """Tests for eval_sessioned function."""

    def test_eval_sessioned(self):
        """Test eval_sessioned function."""
        mock_expr = Mock(spec=Expr)
        mock_app = Mock()

        with patch("pinjected.di.sessioned.eval_applicative") as mock_eval:
            mock_eval.return_value = "eval_result"

            result = eval_sessioned(mock_expr, mock_app)

            assert result == "eval_result"
            mock_eval.assert_called_once_with(mock_expr, mock_app)


class TestSessionedAstContext:
    """Tests for sessioned_ast_context function."""

    def test_sessioned_ast_context(self):
        """Test sessioned_ast_context function."""
        mock_session = Mock()

        result = sessioned_ast_context(mock_session)

        # Check that it returns an AstProxyContextImpl
        from pinjected.di.static_proxy import AstProxyContextImpl

        assert isinstance(result, AstProxyContextImpl)

        # Check the alias name
        assert result._alias_name == "SessionedProxy"

        # Check that eval function is set
        assert result.eval_impl is not None
        assert callable(result.eval_impl)

    def test_sessioned_ast_context_eval_function(self):
        """Test the eval function created by sessioned_ast_context."""
        mock_session = Mock()
        mock_expr = Mock(spec=Expr)

        context = sessioned_ast_context(mock_session)

        # Test the eval function
        with patch("pinjected.di.sessioned.eval_sessioned") as mock_eval:
            mock_eval.return_value = "eval_result"

            result = context.eval_impl(mock_expr)

            assert result == "eval_result"
            # Verify eval_sessioned was called with correct arguments
            mock_eval.assert_called_once()
            args = mock_eval.call_args[0]
            assert args[0] == mock_expr
            # The second argument should be an ApplicativeSesionedImpl
            assert isinstance(args[1], ApplicativeSesionedImpl)
            assert args[1].parent == mock_session


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
