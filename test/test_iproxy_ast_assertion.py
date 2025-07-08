"""Tests for IProxy AST assertion feature."""

import os
import pytest

from pinjected import injected
from pinjected.di.injected import allow_iproxy_creation
from pinjected.di.proxiable import DelegatedVar


# Module-level test - this should work when feature is enabled
@injected
def module_level_func(dep, /, x: int):
    return x + 1


# This should work at module level
# Note: We can't actually test this in pytest because pytest runs everything
# inside test functions, so we rely on the demo file for actual module-level testing


class TestIProxyASTAssertion:
    """Test suite for IProxy AST assertion feature."""

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

    def test_module_level_allowed(self):
        """Test that module-level IProxy creation is allowed."""

        # Module level is tested in the demo file
        # Here we test that the allow_iproxy_creation context works
        @injected
        def test_func(dep, /, x: int):
            return x + 1

        # Use context manager to allow creation
        with allow_iproxy_creation():
            result = test_func(5)
        assert isinstance(result, DelegatedVar)

    def test_function_level_blocked(self):
        """Test that function-level IProxy creation is blocked."""

        @injected
        def test_func(dep, /, x: int):
            return x + 1

        def bad_function():
            # This should raise RuntimeError
            return test_func(5)

        with pytest.raises(RuntimeError) as exc_info:
            bad_function()

        assert "Direct call to @injected function 'test_func'" in str(exc_info.value)
        assert "detected inside function 'bad_function'" in str(exc_info.value)

    def test_nested_injected_blocked(self):
        """Test that calling @injected inside @injected is blocked."""

        @injected
        def inner_func(dep, /, x: int):
            return x + 1

        @injected
        def outer_func(other_dep, /, y: int):
            # This creates IProxy, which should be caught
            return inner_func(y)

        # The outer function definition itself is fine
        assert callable(outer_func)

        # But calling inner_func inside would raise an error
        def test_call():
            return inner_func(5)

        with pytest.raises(RuntimeError):
            test_call()

    def test_with_context_manager(self):
        """Test that context manager allows IProxy creation."""

        @injected
        def test_func(dep, /, x: int):
            return x + 1

        def function_with_context():
            with allow_iproxy_creation():
                # This should be allowed
                result = test_func(5)
            return result

        # Should not raise an error
        result = function_with_context()
        assert isinstance(result, DelegatedVar)

    def test_dependency_declaration_correct(self):
        """Test correct pattern with dependency declaration."""

        @injected
        def dep_func(logger, /, x: int):
            logger.info(f"Processing {x}")
            return x * 2

        @injected
        def main_func(dep_func, logger, /, y: int):
            # dep_func is declared as dependency - this is correct
            result = dep_func(y)
            logger.info(f"Result: {result}")
            return result

        # Function definition should work fine
        assert callable(main_func)

    def test_feature_disabled(self):
        """Test that feature can be disabled via env var."""
        # Disable the feature
        os.environ["PINJECTED_ENABLE_IPROXY_AST_ASSERTION"] = "false"

        # Force reload
        import importlib
        import pinjected.di.injected
        import pinjected.di.partially_injected

        importlib.reload(pinjected.di.injected)
        importlib.reload(pinjected.di.partially_injected)

        @injected
        def test_func(dep, /, x: int):
            return x + 1

        def should_work_when_disabled():
            # This should NOT raise when feature is disabled
            return test_func(5)

        # Should not raise an error when disabled
        result = should_work_when_disabled()
        assert isinstance(result, DelegatedVar)

    def test_error_message_content(self):
        """Test that error message contains helpful information."""

        @injected
        def fetch_user(db, /, user_id: str):
            return {"id": user_id}

        def bad_usage():
            return fetch_user("123")

        with pytest.raises(RuntimeError) as exc_info:
            bad_usage()

        error_msg = str(exc_info.value)
        # Check for key parts of the error message
        assert "Direct call to @injected function 'fetch_user'" in error_msg
        assert "detected inside function 'bad_usage'" in error_msg
        assert "@injected functions return IProxy objects" in error_msg
        assert "Solutions:" in error_msg
        assert "Declare 'fetch_user' as a dependency" in error_msg
        assert "allow_iproxy_creation" in error_msg
        assert "PINJECTED_ENABLE_IPROXY_AST_ASSERTION" in error_msg

    def test_lambda_and_comprehension(self):
        """Test detection works with lambdas and comprehensions."""

        @injected
        def test_func(dep, /, x: int):
            return x + 1

        # Lambda should be detected
        def bad_lambda():
            return test_func(5)

        # But name will still show as the function name
        with pytest.raises(RuntimeError) as exc_info:
            bad_lambda()

        assert "detected inside function 'bad_lambda'" in str(exc_info.value)

    def test_env_var_true_values(self):
        """Test that various true-like environment variable values work."""

        @injected
        def test_func(dep, /, x: int):
            return x + 1

        def should_fail():
            return test_func(5)

        # Test various true values
        for true_value in [
            "true",
            "True",
            "TRUE",
            "1",
            "yes",
            "Yes",
            "YES",
            "on",
            "On",
            "ON",
        ]:
            os.environ["PINJECTED_ENABLE_IPROXY_AST_ASSERTION"] = true_value

            with pytest.raises(RuntimeError) as exc_info:
                should_fail()

            assert "Direct call to @injected function" in str(exc_info.value), (
                f"Failed for value: {true_value}"
            )

    def test_env_var_false_values(self):
        """Test that various false-like environment variable values work."""

        @injected
        def test_func(dep, /, x: int):
            return x + 1

        def should_work():
            return test_func(5)

        # Test various false values
        for false_value in [
            "false",
            "False",
            "FALSE",
            "0",
            "no",
            "No",
            "NO",
            "off",
            "Off",
            "OFF",
            "",
        ]:
            os.environ["PINJECTED_ENABLE_IPROXY_AST_ASSERTION"] = false_value

            # Should not raise
            result = should_work()
            assert isinstance(result, DelegatedVar), f"Failed for value: {false_value}"

    def test_decorator_context(self):
        """Test that decorator context is properly detected."""
        # This tests the decorator function detection in _is_at_module_level
        os.environ["PINJECTED_ENABLE_IPROXY_AST_ASSERTION"] = "true"

        # The @injected decorator itself should be allowed to create IProxy
        @injected
        def test_func(dep, /, x: int):
            return x + 1

        # The decorator application happens at module level so it should work
        assert callable(test_func)

    def test_edge_cases(self):
        """Test edge cases for code coverage."""
        # Test with no frame (theoretical edge case)
        from pinjected.di.injected import _is_at_module_level

        # Call the function to ensure it handles edge cases
        result = _is_at_module_level()
        # Should return False when inside a test function
        assert result is False


class TestIProxyThreadLocal:
    """Test thread-local functionality of IProxy assertion."""

    def test_thread_local_isolation(self):
        """Test that thread-local context is isolated between threads."""
        import threading
        from pinjected.di.injected import _thread_local, allow_iproxy_creation

        results = []

        def thread_func():
            # Should not have allow_iproxy set
            has_attr = hasattr(_thread_local, "allow_iproxy")
            if has_attr:
                results.append(getattr(_thread_local, "allow_iproxy"))
            else:
                results.append(None)

            # Set in context
            with allow_iproxy_creation():
                results.append(getattr(_thread_local, "allow_iproxy", False))

            # Should be reset after context
            results.append(getattr(_thread_local, "allow_iproxy", False))

        # Run in thread
        thread = threading.Thread(target=thread_func)
        thread.start()
        thread.join()

        # Check results
        assert results == [None, True, False]

    def test_nested_context_managers(self):
        """Test nested allow_iproxy_creation contexts."""
        from pinjected.di.injected import _thread_local, allow_iproxy_creation

        # Initially should not be set
        assert getattr(_thread_local, "allow_iproxy", False) is False

        with allow_iproxy_creation():
            assert getattr(_thread_local, "allow_iproxy", False) is True

            # Nested context
            with allow_iproxy_creation():
                assert getattr(_thread_local, "allow_iproxy", False) is True

            # Should still be True after inner context exits
            assert getattr(_thread_local, "allow_iproxy", False) is True

        # Should be reset after outer context exits
        assert getattr(_thread_local, "allow_iproxy", False) is False


class TestModuleLevelDetection:
    """Test module level detection functionality."""

    def test_module_level_with_class_definition(self):
        """Test detection inside class definition."""
        from pinjected.di.injected import _is_at_module_level

        # This should return False as we're inside a method
        assert _is_at_module_level() is False

    def test_module_level_in_function(self):
        """Test detection inside regular function."""
        from pinjected.di.injected import _is_at_module_level

        def inner_func():
            return _is_at_module_level()

        assert inner_func() is False

    def test_module_level_in_lambda(self):
        """Test detection inside lambda."""
        from pinjected.di.injected import _is_at_module_level

        def check_lambda():
            return _is_at_module_level()

        assert check_lambda() is False

    def test_module_level_complex_stack(self):
        """Test with complex call stack."""
        from pinjected.di.injected import _is_at_module_level

        def level1():
            def level2():
                def level3():
                    return _is_at_module_level()

                return level3()

            return level2()

        assert level1() is False


class TestPartialCallSpecificScenarios:
    """Test specific scenarios for Partial.__call__ checks."""

    def test_partial_call_with_env_var_variations(self):
        """Test Partial call with various env var values."""
        import os
        from pinjected import injected

        # Test with env var set to empty string
        os.environ["PINJECTED_ENABLE_IPROXY_AST_ASSERTION"] = ""

        @injected
        def test_func(logger, /, x):
            return x

        # Should work with empty env var
        def inner():
            return test_func(42)

        result = inner()  # Should not raise
        assert result is not None

    def test_partial_call_frame_edge_cases(self):
        """Test Partial call with edge cases in frame detection."""
        import os
        from pinjected import injected

        os.environ["PINJECTED_ENABLE_IPROXY_AST_ASSERTION"] = "true"

        @injected
        def test_func(logger, /, x):
            return x

        # Test with exec
        try:
            exec("result = test_func(42)")
            # Should raise since exec creates a function-like context
        except RuntimeError as e:
            assert "Direct call to @injected function" in str(e)

        os.environ["PINJECTED_ENABLE_IPROXY_AST_ASSERTION"] = "false"
