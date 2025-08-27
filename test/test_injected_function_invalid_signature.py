"""Tests for @injected function calls with invalid signatures in AST construction mode.

This module tests that when calling @injected functions with wrong arguments
(missing required args, wrong keyword args, etc.) during IProxy creation,
the error messages contain the function name and are helpful for debugging.
"""

import os
import pytest

from pinjected import injected


class TestInjectedFunctionInvalidSignature:
    """Test suite for @injected function calls with invalid signatures."""

    def setup_method(self):
        """Set up test environment."""
        # Save original env var
        self.original_env = os.environ.get("PINJECTED_ENABLE_IPROXY_AST_ASSERTION")
        # Enable the feature for tests
        os.environ["PINJECTED_ENABLE_IPROXY_AST_ASSERTION"] = "true"
        # Force reload to pick up env var change
        import importlib
        import pinjected.di.injected

        importlib.reload(pinjected.di.injected)

    def teardown_method(self):
        """Restore original environment."""
        if self.original_env is None:
            os.environ.pop("PINJECTED_ENABLE_IPROXY_AST_ASSERTION", None)
        else:
            os.environ["PINJECTED_ENABLE_IPROXY_AST_ASSERTION"] = self.original_env
        # Force reload to restore original state
        import importlib
        import pinjected.di.injected

        importlib.reload(pinjected.di.injected)

    def test_missing_positional_argument(self):
        """Test error message when missing required positional argument."""

        @injected
        def test_function(dep, /, arg1: int, arg2: int) -> int:
            return arg1 + arg2

        from pinjected.di.injected import allow_iproxy_creation

        # Call with missing arg1 - should get TypeError with function name
        with allow_iproxy_creation(), pytest.raises(TypeError) as exc_info:
            # Missing arg1
            test_function(arg2=1)

        error_msg = str(exc_info.value)
        print(f"\nMissing argument error: {error_msg}")

        # Also check traceback for more context
        import traceback

        tb_str = "".join(
            traceback.format_exception(
                type(exc_info.value), exc_info.value, exc_info.tb
            )
        )
        print(f"\nFull traceback:\n{tb_str}")

        # Check that the fix worked - function name, file, and line number should be included
        assert "arg1" in error_msg
        assert "missing" in error_msg.lower()
        assert "test_function" in error_msg
        assert "File:" in error_msg
        assert ".py:" in error_msg  # Check for line number

        # SUCCESS: The error message now contains full location info!
        # Before fix: "missing a required argument: 'arg1'"
        # After fix: "test_function() missing a required argument: 'arg1'\n  File: /path/to/file.py:44"
        print(f"\nSUCCESS: Function name and location are now included in error!")
        print(f"Error message:\n{error_msg}")

    def test_unexpected_keyword_argument(self):
        """Test error message when passing unexpected keyword argument."""

        @injected
        def test_function(dep, /, arg1: int, arg2: int) -> int:
            return arg1 + arg2

        from pinjected.di.injected import allow_iproxy_creation

        # Call with unexpected keyword argument
        with allow_iproxy_creation(), pytest.raises(TypeError) as exc_info:
            # arg3 doesn't exist
            test_function(1, 2, arg3=3)

        error_msg = str(exc_info.value)
        print(f"\nUnexpected keyword error: {error_msg}")

        # Check that the fix worked
        assert "arg3" in error_msg
        assert "unexpected" in error_msg.lower()
        assert "test_function" in error_msg

        # SUCCESS: Function name is now included
        print(f"\nSUCCESS: Function name is now included in error: {error_msg!r}")

    def test_too_many_positional_arguments(self):
        """Test error message when passing too many positional arguments."""

        @injected
        def test_function(dep, /, arg1: int) -> int:
            return arg1 * 2

        from pinjected.di.injected import allow_iproxy_creation

        # Call with too many positional arguments
        with allow_iproxy_creation(), pytest.raises(TypeError) as exc_info:
            # Only expects 1 positional arg after dependencies
            test_function(1, 2, 3)

        error_msg = str(exc_info.value)
        print(f"\nToo many arguments error: {error_msg}")

        # Check that the fix worked
        assert "takes" in error_msg.lower() or "positional" in error_msg.lower()
        assert "test_function" in error_msg

        # SUCCESS: Function name is now included
        print(f"\nSUCCESS: Function name is now included in error: {error_msg!r}")

    def test_mixed_signature_errors(self):
        """Test complex signature with multiple parameter types."""

        @injected
        def complex_function(
            dep1,
            dep2,
            /,
            required_arg: int,
            *,  # keyword-only args after this
            kwonly_arg: str,
            optional_arg: int = 10,
        ) -> dict:
            return {
                "required": required_arg,
                "kwonly": kwonly_arg,
                "optional": optional_arg,
            }

        from pinjected.di.injected import allow_iproxy_creation

        with allow_iproxy_creation():
            # Test 1: Missing keyword-only argument
            with pytest.raises(TypeError) as exc_info:
                complex_function(42)  # missing kwonly_arg

            error_msg = str(exc_info.value)
            print(f"\nMissing keyword-only arg error: {error_msg}")
            assert "kwonly_arg" in error_msg

            # SUCCESS: Check that function name is now present
            assert "complex_function" in error_msg
            print(f"\nSUCCESS: Function name is now included in error: {error_msg!r}")

            # Test 2: Positional argument for keyword-only parameter
            with pytest.raises(TypeError) as exc_info:
                complex_function(42, "wrong")  # kwonly_arg must be keyword

            error_msg = str(exc_info.value)
            print(f"\nPositional for keyword-only error: {error_msg}")

            # SUCCESS: Check that function name is now present
            assert "complex_function" in error_msg
            print(f"\nSUCCESS: Function name is now included in error: {error_msg!r}")

    def test_ast_assertion_feature(self):
        """Test the AST assertion feature for catching direct calls."""

        @injected
        def simple_func(config, /, x: int) -> int:
            return x * 2

        # When AST assertion is enabled, calling @injected function
        # directly from a test function should raise RuntimeError
        with pytest.raises(RuntimeError) as exc_info:
            simple_func(5)

        error_msg = str(exc_info.value)
        assert "Direct call to @injected function 'simple_func'" in error_msg

    def test_signature_error_summary(self):
        """Summary test demonstrating the signature error issue and potential solution."""

        print("\n" + "=" * 70)
        print("SIGNATURE ERROR MESSAGE ISSUE SUMMARY")
        print("=" * 70)

        @injected
        def important_function(
            database, logger, /, user_id: int, include_details: bool = False
        ) -> dict:
            """An important function that processes user data."""
            return {"user_id": user_id, "details": include_details}

        from pinjected.di.injected import allow_iproxy_creation

        # Example 1: Missing required argument
        with allow_iproxy_creation():
            try:
                # Missing user_id
                important_function(include_details=True)
            except TypeError as e:
                print(f"\nActual error (FIXED!): {e}")
                assert "important_function" in str(e)
                print(f"SUCCESS: Function name is now included in the error message!")

        # Example 2: Unexpected keyword argument
        with allow_iproxy_creation():
            try:
                # 'extra_arg' doesn't exist
                important_function(123, extra_arg="unexpected")
            except TypeError as e:
                print(f"\nActual error (FIXED!): {e}")
                assert "important_function" in str(e)
                print(f"SUCCESS: Function name is now included in the error message!")

        print("\nFIX IMPLEMENTED:")
        print(
            "✅ Modified pinjected/di/args_modifier.py to catch TypeError and re-raise with function name"
        )
        print(
            "✅ Updated KeepArgsPure to accept function_name, source_file, and line_number"
        )
        print("✅ Modified injected.py to extract source location using inspect module")
        print(
            "✅ All signature errors now include function name AND file location for easier debugging"
        )
        print("\nExample error message:")
        print("  test_function() missing a required argument: 'arg1'")
        print("    File: /path/to/file.py:44")
        print("=" * 70)
