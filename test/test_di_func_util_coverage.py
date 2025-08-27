"""Comprehensive tests for di/func_util.py module."""

import pytest
from unittest.mock import patch, MagicMock

from pinjected.di.func_util import MissingRequiredArgumentError, fix_args_kwargs


class TestMissingRequiredArgumentError:
    """Test the MissingRequiredArgumentError exception."""

    def test_is_value_error(self):
        """Test that MissingRequiredArgumentError is a ValueError."""
        assert issubclass(MissingRequiredArgumentError, ValueError)

    def test_can_raise_and_catch(self):
        """Test raising and catching the exception."""
        with pytest.raises(MissingRequiredArgumentError):
            raise MissingRequiredArgumentError("Missing argument")

    def test_with_message(self):
        """Test exception with message."""
        msg = "Argument 'foo' is required"
        exc = MissingRequiredArgumentError(msg)
        assert str(exc) == msg


class TestFixArgsKwargs:
    """Test the fix_args_kwargs function."""

    def test_simple_function(self):
        """Test with simple function."""

        def func(a, b):
            return a + b

        args, kwargs = fix_args_kwargs(func, (1, 2), {})
        assert args == [1, 2]
        assert kwargs == {}

    def test_function_with_defaults(self):
        """Test function with default arguments."""

        def func(a, b=10):
            return a + b

        # Without default
        args, kwargs = fix_args_kwargs(func, (1, 2), {})
        assert args == [1, 2]
        assert kwargs == {}

        # With default applied
        args, kwargs = fix_args_kwargs(func, (1,), {})
        assert args == [1, 10]
        assert kwargs == {}

    def test_keyword_only_args(self):
        """Test function with keyword-only arguments."""

        def func(a, *, b, c=30):
            return a + b + c

        args, kwargs = fix_args_kwargs(func, (10,), {"b": 20})
        assert args == [10]
        assert kwargs == {"b": 20, "c": 30}

    def test_var_positional(self):
        """Test function with *args."""

        def func(a, *args):
            return sum([a] + list(args))

        args, kwargs = fix_args_kwargs(func, (1, 2, 3, 4), {})
        assert args == [1, 2, 3, 4]
        assert kwargs == {}

    def test_var_keyword(self):
        """Test function with **kwargs."""

        def func(a, **kwargs):
            return kwargs

        args, kwargs = fix_args_kwargs(func, (1,), {"x": 2, "y": 3})
        assert args == [1]
        assert kwargs == {"x": 2, "y": 3}

    def test_positional_only(self):
        """Test function with positional-only arguments."""

        def func(a, b, /, c):
            return a + b + c

        args, kwargs = fix_args_kwargs(func, (1, 2, 3), {})
        assert args == [1, 2, 3]
        assert kwargs == {}

    def test_mixed_parameters(self):
        """Test function with all parameter types."""

        def func(a, b, /, c, d=4, *args, e, f=6, **kwargs):
            return sum([a, b, c, d, e, f] + list(args)) + sum(kwargs.values())

        args, kwargs = fix_args_kwargs(
            func, (1, 2, 3, 5, 7, 8), {"e": 9, "x": 10, "y": 11}
        )
        assert args == [1, 2, 3, 5, 7, 8]
        assert kwargs == {"e": 9, "f": 6, "x": 10, "y": 11}

    def test_kwargs_passed_as_positional(self):
        """Test keyword arguments passed positionally."""

        def func(a, b, c):
            return a + b + c

        # Pass all as positional
        args, kwargs = fix_args_kwargs(func, (1, 2, 3), {})
        assert args == [1, 2, 3]
        assert kwargs == {}

        # Mix positional and keyword
        args, kwargs = fix_args_kwargs(func, (1,), {"b": 2, "c": 3})
        assert args == [1, 2, 3]
        assert kwargs == {}

    def test_builtin_function(self):
        """Test with builtin function that has no signature."""
        # Built-in functions like len don't have signatures
        with patch("inspect.signature", side_effect=ValueError("no signature")):
            args, kwargs = fix_args_kwargs(len, ([1, 2, 3],), {})
            # Should return original args/kwargs when signature fails
            assert args == ([1, 2, 3],)
            assert kwargs == {}

    def test_c_function_no_signature(self):
        """Test with C function that has no Python signature."""
        # Mock a C function
        mock_func = MagicMock()

        with patch("inspect.signature", side_effect=ValueError("no signature")):
            original_args = (1, 2, 3)
            original_kwargs = {"a": 4, "b": 5}

            args, kwargs = fix_args_kwargs(mock_func, original_args, original_kwargs)

            # Should return originals unchanged
            assert args == original_args
            assert kwargs == original_kwargs

    @patch("pinjected.di.func_util.logger")
    def test_logging(self, mock_logger):
        """Test that function logs the fixed args/kwargs."""

        def func(a, b=2):
            return a + b

        args, kwargs = fix_args_kwargs(func, (1,), {})

        # Check that logger.info was called
        mock_logger.info.assert_called()
        # Check the log message contains the fixed values
        log_call = mock_logger.info.call_args[0][0]
        assert "fixed:" in log_call
        assert "[1, 2]" in log_call
        assert "{}" in log_call

    def test_empty_function(self):
        """Test function with no parameters."""

        def func():
            return 42

        args, kwargs = fix_args_kwargs(func, (), {})
        assert args == []
        assert kwargs == {}

    def test_lambda_function(self):
        """Test with lambda function."""

        def func(x, y=5):
            return x * y

        args, kwargs = fix_args_kwargs(func, (3,), {})
        assert args == [3, 5]
        assert kwargs == {}

    def test_class_method(self):
        """Test with class method."""

        class MyClass:
            def method(self, a, b):
                return a + b

        obj = MyClass()
        args, kwargs = fix_args_kwargs(obj.method, (1, 2), {})
        assert args == [1, 2]
        assert kwargs == {}

    def test_static_method(self):
        """Test with static method."""

        class MyClass:
            @staticmethod
            def method(a, b):
                return a + b

        args, kwargs = fix_args_kwargs(MyClass.method, (1, 2), {})
        assert args == [1, 2]
        assert kwargs == {}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
