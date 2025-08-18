"""Tests for pinjected.di.func_util module."""

import pytest
from unittest.mock import patch
from pinjected.di.func_util import fix_args_kwargs, MissingRequiredArgumentError


class TestFuncUtil:
    """Tests for func_util module."""

    def test_missing_required_argument_error(self):
        """Test MissingRequiredArgumentError exception."""
        error = MissingRequiredArgumentError("Missing argument")
        assert isinstance(error, ValueError)
        assert str(error) == "Missing argument"

    def test_fix_args_kwargs_normal_function(self):
        """Test fix_args_kwargs with a normal function."""

        def test_func(a, b=2, c=3):
            return a + b + c

        args = (1,)
        kwargs = {"c": 5}

        fixed_args, fixed_kwargs = fix_args_kwargs(test_func, args, kwargs)

        # The function returns a list of all positional args with defaults applied
        assert fixed_args == [1, 2, 5]  # a=1, b=2 (default), c=5
        assert fixed_kwargs == {}  # No keyword-only args

    def test_fix_args_kwargs_with_defaults(self):
        """Test fix_args_kwargs applies defaults."""

        def test_func(a, b=10, c=20):
            return a + b + c

        args = (5,)
        kwargs = {}

        fixed_args, fixed_kwargs = fix_args_kwargs(test_func, args, kwargs)

        # Defaults should be applied
        assert fixed_args == [5, 10, 20]  # All positional args with defaults
        assert fixed_kwargs == {}

    def test_fix_args_kwargs_with_inspect_signature_error(self):
        """Test fix_args_kwargs when inspect.signature raises ValueError."""

        # Create a mock function that causes inspect.signature to fail
        def mock_func():
            pass

        # Mock inspect.signature to raise ValueError
        with patch("inspect.signature") as mock_signature:
            mock_signature.side_effect = ValueError("Cannot get signature")

            args = (1, 2, 3)
            kwargs = {"key": "value"}

            # When inspect.signature fails, the function should return args/kwargs unchanged
            fixed_args, fixed_kwargs = fix_args_kwargs(mock_func, args, kwargs)

            assert fixed_args == args
            assert fixed_kwargs == kwargs
            assert mock_signature.called

    def test_fix_args_kwargs_with_builtin_function(self):
        """Test fix_args_kwargs with a built-in function that might not have signature."""
        # Some built-in functions may raise ValueError when getting signature
        # We'll test with a function that simulates this behavior

        class BuiltinLike:
            """Simulates a built-in function behavior."""

            def __call__(self, *args, **kwargs):
                return args, kwargs

        builtin_like = BuiltinLike()

        # Test with the builtin-like object
        args = (1, 2)
        kwargs = {"a": 3}

        # This should work without raising an exception
        fixed_args, fixed_kwargs = fix_args_kwargs(builtin_like, args, kwargs)

        # The result depends on whether inspect.signature works for this object
        assert isinstance(fixed_args, (list, tuple))
        assert isinstance(fixed_kwargs, dict)

    def test_fix_args_kwargs_all_kwargs(self):
        """Test fix_args_kwargs with all keyword arguments."""

        def test_func(a, b, c=3):
            return a + b + c

        args = ()
        kwargs = {"a": 1, "b": 2, "c": 4}

        fixed_args, fixed_kwargs = fix_args_kwargs(test_func, args, kwargs)

        # All args become positional in the output
        assert fixed_args == [1, 2, 4]
        assert fixed_kwargs == {}

    def test_fix_args_kwargs_mixed_args(self):
        """Test fix_args_kwargs with mixed positional and keyword arguments."""

        def test_func(x, y, z=None, w=10):
            return x, y, z, w

        args = (1, 2)
        kwargs = {"z": 3}

        fixed_args, fixed_kwargs = fix_args_kwargs(test_func, args, kwargs)

        # All positional args with defaults applied
        assert fixed_args == [1, 2, 3, 10]  # x=1, y=2, z=3, w=10 (default)
        assert fixed_kwargs == {}

    def test_fix_args_kwargs_keyword_only(self):
        """Test fix_args_kwargs with keyword-only arguments."""

        def test_func(a, b, *, kw1, kw2=20):
            return a, b, kw1, kw2

        args = (1, 2)
        kwargs = {"kw1": 10}

        fixed_args, fixed_kwargs = fix_args_kwargs(test_func, args, kwargs)

        # Positional args
        assert fixed_args == [1, 2]
        # Keyword-only args
        assert fixed_kwargs == {"kw1": 10, "kw2": 20}

    def test_fix_args_kwargs_var_positional(self):
        """Test fix_args_kwargs with *args (VAR_POSITIONAL)."""

        def test_func(a, b, *args, kw=None):
            return a, b, args, kw

        args = (1, 2, 3, 4, 5)
        kwargs = {"kw": "test"}

        fixed_args, fixed_kwargs = fix_args_kwargs(test_func, args, kwargs)

        # First two are regular positional, rest go to *args
        assert fixed_args == [1, 2, 3, 4, 5]
        assert fixed_kwargs == {"kw": "test"}

    def test_fix_args_kwargs_var_keyword(self):
        """Test fix_args_kwargs with **kwargs (VAR_KEYWORD)."""

        def test_func(a, b=2, **kwargs):
            return a, b, kwargs

        args = (1,)
        kwargs = {"b": 3, "extra1": "value1", "extra2": "value2"}

        fixed_args, fixed_kwargs = fix_args_kwargs(test_func, args, kwargs)

        # Regular args
        assert fixed_args == [1, 3]
        # Extra kwargs go to **kwargs
        assert fixed_kwargs == {"extra1": "value1", "extra2": "value2"}

    def test_fix_args_kwargs_var_positional_and_keyword(self):
        """Test fix_args_kwargs with both *args and **kwargs."""

        def test_func(a, *args, kw=None, **kwargs):
            return a, args, kw, kwargs

        args = (1, 2, 3)
        kwargs = {"kw": "test", "extra": "value"}

        fixed_args, fixed_kwargs = fix_args_kwargs(test_func, args, kwargs)

        # First is regular positional, rest go to *args
        assert fixed_args == [1, 2, 3]
        # kw is keyword-only, extra goes to **kwargs
        assert fixed_kwargs == {"kw": "test", "extra": "value"}

    def test_fix_args_kwargs_empty_var_args(self):
        """Test fix_args_kwargs with *args and **kwargs but no extra args."""

        def test_func(a, *args, **kwargs):
            return a, args, kwargs

        args = (1,)
        kwargs = {}

        fixed_args, fixed_kwargs = fix_args_kwargs(test_func, args, kwargs)

        # Only the required arg, no extra args
        assert fixed_args == [1]
        assert fixed_kwargs == {}

    def test_fix_args_kwargs_positional_only(self):
        """Test fix_args_kwargs with positional-only parameters (Python 3.8+)."""

        def test_func(a, b, /, c=3):
            return a, b, c

        args = (1, 2)
        kwargs = {"c": 4}

        fixed_args, fixed_kwargs = fix_args_kwargs(test_func, args, kwargs)

        # All become positional args
        assert fixed_args == [1, 2, 4]
        assert fixed_kwargs == {}

    @patch("pinjected.di.func_util.logger")
    def test_fix_args_kwargs_logging(self, mock_logger):
        """Test that fix_args_kwargs logs the fixed args."""

        def test_func(a, b=2):
            return a + b

        args = (1,)
        kwargs = {}

        fixed_args, fixed_kwargs = fix_args_kwargs(test_func, args, kwargs)

        # Check that logger.info was called
        mock_logger.info.assert_called_once()
        log_message = mock_logger.info.call_args[0][0]
        assert "fixed:" in log_message
        assert "[1, 2]" in log_message
        assert "{}" in log_message


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
