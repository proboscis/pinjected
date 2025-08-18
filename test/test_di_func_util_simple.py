"""Simple tests for di/func_util.py module."""

import pytest
from unittest.mock import patch

from pinjected.di.func_util import fix_args_kwargs, MissingRequiredArgumentError


class TestFuncUtil:
    """Test the func_util module functionality."""

    def test_missing_required_argument_error(self):
        """Test MissingRequiredArgumentError is a ValueError."""
        assert issubclass(MissingRequiredArgumentError, ValueError)

        # Test creating instance
        error = MissingRequiredArgumentError("Missing arg")
        assert isinstance(error, ValueError)
        assert str(error) == "Missing arg"

    def test_fix_args_kwargs_simple(self):
        """Test fix_args_kwargs with simple function."""

        def func(a, b, c=3):
            pass

        args, kwargs = fix_args_kwargs(func, (1, 2), {})
        assert args == [1, 2, 3]  # Default applied
        assert kwargs == {}

    def test_fix_args_kwargs_with_kwargs(self):
        """Test fix_args_kwargs with keyword arguments."""

        def func(a, b, c=3):
            pass

        args, kwargs = fix_args_kwargs(func, (1,), {"b": 2, "c": 4})
        assert args == [1, 2, 4]
        assert kwargs == {}

    def test_fix_args_kwargs_keyword_only(self):
        """Test fix_args_kwargs with keyword-only arguments."""

        def func(a, *, b, c=3):
            pass

        args, kwargs = fix_args_kwargs(func, (1,), {"b": 2})
        assert args == [1]
        assert kwargs == {"b": 2, "c": 3}

    def test_fix_args_kwargs_var_positional(self):
        """Test fix_args_kwargs with *args."""

        def func(a, *args, b=2):
            pass

        args, kwargs = fix_args_kwargs(func, (1, 2, 3, 4), {"b": 5})
        assert args == [1, 2, 3, 4]
        assert kwargs == {"b": 5}

    def test_fix_args_kwargs_var_keyword(self):
        """Test fix_args_kwargs with **kwargs."""

        def func(a, **kwargs):
            pass

        args, kwargs = fix_args_kwargs(func, (1,), {"b": 2, "c": 3})
        assert args == [1]
        assert kwargs == {"b": 2, "c": 3}

    def test_fix_args_kwargs_positional_only(self):
        """Test fix_args_kwargs with positional-only arguments."""
        # Use exec to create function with positional-only params
        exec(
            """
def func(a, b, /, c, *, d):
    pass
""",
            globals(),
        )

        func = globals()["func"]
        args, kwargs = fix_args_kwargs(func, (1, 2, 3), {"d": 4})
        assert args == [1, 2, 3]
        assert kwargs == {"d": 4}

    def test_fix_args_kwargs_no_signature(self):
        """Test fix_args_kwargs with function that has no signature."""
        # Built-in functions like len don't have signatures
        args, kwargs = fix_args_kwargs(len, ([1, 2, 3],), {})
        # When no signature, it converts args to list
        assert args == [[1, 2, 3]]  # Converted to list
        assert kwargs == {}

    @patch("pinjected.di.func_util.logger")
    def test_fix_args_kwargs_logging(self, mock_logger):
        """Test that fix_args_kwargs logs the fixed args."""

        def func(a, b):
            pass

        args, kwargs = fix_args_kwargs(func, (1, 2), {})

        # Check logger.info was called
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert "fixed:" in call_args
        assert "[1, 2]" in call_args


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
