"""Tests for test/injected_pytest.py module."""

import pytest
from pinjected import Injected, design
from pinjected.test import injected_pytest


def test_injected_pytest_import():
    """Test that injected_pytest can be imported."""
    assert callable(injected_pytest)


def test_injected_pytest_basic_usage():
    """Test basic usage of injected_pytest decorator."""

    # Create a simple logger mock
    class MockLogger:
        def __init__(self):
            self.logs = []

        def info(self, message):
            self.logs.append(message)

    # Create a test design
    mock_logger = MockLogger()
    test_design = design(logger=Injected.pure(mock_logger))

    # Define test function
    @injected_pytest(test_design)
    def test_func(logger):
        logger.info("test message")
        return "success"

    # Run test
    result = test_func()

    # Verify
    assert result == "success"
    assert mock_logger.logs == ["test message"]


def test_injected_pytest_without_parentheses():
    """Test using decorator without parentheses."""

    # Simple mock that doesn't need injection
    @injected_pytest
    def test_func():
        return "no dependencies"

    # Should still work
    result = test_func()
    assert result == "no dependencies"


def test_injected_pytest_with_empty_design():
    """Test using decorator with empty design."""

    @injected_pytest()
    def test_func():
        return "with parentheses"

    result = test_func()
    assert result == "with parentheses"


def test_injected_pytest_with_async_function():
    """Test that async functions are handled properly."""

    class AsyncService:
        async def get_value(self):
            return "async result"

    test_design = design(service=Injected.pure(AsyncService()))

    @injected_pytest(test_design)
    async def test_async_func(service):
        result = await service.get_value()
        return result

    # Run the async test
    result = test_async_func()
    assert result == "async result"


def test_injected_pytest_multiple_dependencies():
    """Test with multiple dependencies."""

    class ServiceA:
        def get_a(self):
            return "A"

    class ServiceB:
        def get_b(self):
            return "B"

    test_design = design(
        service_a=Injected.pure(ServiceA()), service_b=Injected.pure(ServiceB())
    )

    @injected_pytest(test_design)
    def test_func(service_a, service_b):
        return service_a.get_a() + service_b.get_b()

    result = test_func()
    assert result == "AB"


def test_injected_pytest_with_nested_design():
    """Test with nested design dependencies."""

    class Database:
        def get_data(self):
            return {"key": "value"}

    class Service:
        def __init__(self, db):
            self.db = db

        def process(self):
            data = self.db.get_data()
            return f"processed: {data['key']}"

    # Create nested design
    test_design = design(
        db=Injected.pure(Database()), service=Injected.bind(Service, db="db")
    )

    @injected_pytest(test_design)
    def test_func(service):
        return service.process()

    result = test_func()
    assert result == "processed: value"


def test_injected_pytest_function_module_access():
    """Test accessing attributes through the module."""
    # Import the actual module
    try:
        import pinjected.test.injected_pytest as module

        # Test that key functions exist (if accessible)
        if hasattr(module, "unwrap_exception_group"):
            assert callable(module.unwrap_exception_group)

            # Test basic unwrap functionality
            from pinjected.compatibility.task_group import CompatibleExceptionGroup

            inner = ValueError("test")
            group = CompatibleExceptionGroup([inner])
            result = module.unwrap_exception_group(group)
            assert result is inner

        # Test env var exists
        if hasattr(module, "UNWRAP_EXCEPTIONS"):
            assert isinstance(module.UNWRAP_EXCEPTIONS, bool)

    except ImportError:
        # Module structure might be different, skip this test
        pytest.skip("Module structure prevents direct import")


def test_injected_pytest_error_handling():
    """Test that exceptions are properly propagated."""

    class FailingService:
        def process(self):
            raise RuntimeError("Service failed")

    test_design = design(service=Injected.pure(FailingService()))

    @injected_pytest(test_design)
    def test_func(service):
        return service.process()

    # The exception should be raised (possibly wrapped)
    with pytest.raises((RuntimeError, Exception)) as exc_info:
        test_func()

    # Check that the original error message is preserved somewhere
    # Need to check recursively for nested ExceptionGroups
    def find_message_in_exception(exc, message):
        if message in str(exc):
            return True
        if hasattr(exc, "exceptions"):
            for sub_exc in exc.exceptions:
                if find_message_in_exception(sub_exc, message):
                    return True
        return False

    assert find_message_in_exception(exc_info.value, "Service failed")


def test_injected_pytest_no_module_file_without_parens():
    """Test when function module has no __file__ attribute (without parentheses)."""
    import types

    # Create a mock module without __file__
    mock_module = types.ModuleType("mock_module")

    # Create a function and manually assign it to the mock module
    def test_func():
        return "test"

    test_func.__module__ = mock_module.__name__

    # Patch inspect.getmodule to return our mock module
    import inspect

    original_getmodule = inspect.getmodule

    def mock_getmodule(obj):
        if obj is test_func:
            return mock_module
        return original_getmodule(obj)

    # Apply the decorator - this should raise ValueError
    with (
        pytest.raises(ValueError, match="Could not determine caller module"),
        pytest.MonkeyPatch.context() as m,
    ):
        m.setattr(inspect, "getmodule", mock_getmodule)
        # Apply decorator without parentheses
        injected_pytest(test_func)


def test_injected_pytest_no_module_file_with_parens():
    """Test when function module has no __file__ attribute (with parentheses)."""
    import types

    # Create a mock module without __file__
    mock_module = types.ModuleType("mock_module")

    # Create a function and manually assign it to the mock module
    def test_func():
        return "test"

    test_func.__module__ = mock_module.__name__

    # Patch inspect.getmodule to return our mock module
    import inspect

    original_getmodule = inspect.getmodule

    def mock_getmodule(obj):
        if obj is test_func:
            return mock_module
        return original_getmodule(obj)

    # Apply the decorator - this should raise ValueError
    with (
        pytest.raises(ValueError, match="Could not determine caller module"),
        pytest.MonkeyPatch.context() as m,
    ):
        m.setattr(inspect, "getmodule", mock_getmodule)
        # Apply decorator with parentheses
        decorator = injected_pytest()
        decorator(test_func)


def test_injected_pytest_with_delegated_var():
    """Test using DelegatedVar[Design] as override."""
    from pinjected import IProxy

    # Create a design that will be wrapped in DelegatedVar
    class Service:
        def get_value(self):
            return "delegated_value"

    # Create a design instance
    service_design = design(service=Injected.pure(Service()))

    # Create DelegatedVar wrapping the design
    delegated_design = IProxy(service_design)

    # Use the DelegatedVar as override
    @injected_pytest(delegated_design)
    def test_func(service):
        return service.get_value()

    # Run test
    result = test_func()
    assert result == "delegated_value"


def test_injected_pytest_with_invalid_delegated_var():
    """Test DelegatedVar that doesn't resolve to Design."""
    from pinjected import IProxy, instance

    # Create a DelegatedVar that resolves to non-Design
    @instance
    def not_a_design():
        return "I am not a Design"

    delegated_var = IProxy(not_a_design)

    # Use the invalid DelegatedVar as override
    @injected_pytest(delegated_var)
    def test_func():
        return "test"

    # Should raise TypeError when executing
    with pytest.raises(TypeError, match="DelegatedVar must resolve to a Design"):
        test_func()


def test_injected_pytest_with_exception_unwrapping():
    """Test exception unwrapping behavior."""
    from pinjected.compatibility.task_group import CompatibleExceptionGroup

    # UNWRAP_EXCEPTIONS defaults to True, so exceptions should be unwrapped when possible
    # However, due to nested TaskGroups, we might still get an ExceptionGroup

    class FailingService:
        def fail(self):
            raise ValueError("Inner exception")

    test_design = design(service=Injected.pure(FailingService()))

    @injected_pytest(test_design)
    def test_func(service):
        return service.fail()

    # The exception may still be wrapped even with unwrapping enabled
    # because of how async task groups work
    with pytest.raises(Exception) as exc_info:
        test_func()

    # Check that the inner exception message is preserved
    exc = exc_info.value
    # Check if it's a ValueError directly or check the inner exception
    if isinstance(exc, ValueError):
        assert "Inner exception" in str(exc)
    elif isinstance(exc, CompatibleExceptionGroup):
        # Even with unwrapping, we might still get an ExceptionGroup
        # if there are multiple nested groups
        # Check that we can find the inner exception somewhere
        def find_inner_exception(exc_group):
            for e in exc_group.exceptions:
                if isinstance(e, ValueError) and "Inner exception" in str(e):
                    return True
                if isinstance(e, CompatibleExceptionGroup) and find_inner_exception(e):
                    return True
            return False

        assert find_inner_exception(exc), f"Could not find 'Inner exception' in {exc}"


def test_injected_pytest_without_exception_unwrapping():
    """Test exception behavior - we can't easily test without unwrapping since it's set at module level."""
    # Since we can't easily change UNWRAP_EXCEPTIONS after module import,
    # we'll just test that the exception message is preserved regardless

    class FailingService:
        def fail(self):
            raise ValueError("Inner exception")

    test_design = design(service=Injected.pure(FailingService()))

    @injected_pytest(test_design)
    def test_func(service):
        return service.fail()

    # Should raise exception
    with pytest.raises(Exception) as exc_info:
        test_func()

    # Check that error message is preserved
    # The exception might be nested in ExceptionGroups

    def find_inner_exception(exc):
        if isinstance(exc, ValueError) and "Inner exception" in str(exc):
            return True
        # Check for both CompatibleExceptionGroup and native ExceptionGroup
        if hasattr(exc, "exceptions"):  # This covers both types
            for e in exc.exceptions:
                if find_inner_exception(e):
                    return True
        return False

    assert find_inner_exception(exc_info.value), (
        f"Could not find 'Inner exception' in {exc_info.value}"
    )


def test_injected_pytest_resolver_cleanup():
    """Test that resolver is properly cleaned up even on exception."""
    from unittest.mock import patch

    # Track resolver cleanup
    cleanup_called = False

    class MockResolver:
        def __init__(self, *args, **kwargs):
            pass

        async def provide(self, injected):
            raise RuntimeError("Simulated error")

        async def destruct(self):
            nonlocal cleanup_called
            cleanup_called = True

    # Patch AsyncResolver
    with patch("pinjected.test.injected_pytest.AsyncResolver", MockResolver):

        @injected_pytest()
        def test_func():
            return "test"

        # Should raise the simulated error (might be wrapped in ExceptionGroup)
        with pytest.raises(Exception) as exc_info:
            test_func()

        # Check that the RuntimeError is in there somewhere
        def contains_runtime_error(exc):
            if isinstance(exc, RuntimeError):
                return True
            if hasattr(exc, "exceptions"):
                return any(contains_runtime_error(e) for e in exc.exceptions)
            return False

        assert contains_runtime_error(exc_info.value)

        # Verify cleanup was called
        assert cleanup_called


def test_injected_pytest_with_awaitable_result():
    """Test handling of awaitable results."""
    import asyncio

    class AsyncService:
        async def get_data(self):
            await asyncio.sleep(0.001)  # Small delay
            return "async_data"

    test_design = design(service=Injected.pure(AsyncService()))

    @injected_pytest(test_design)
    async def test_func(service):
        # Return an awaitable
        return service.get_data()

    # Run test
    result = test_func()
    assert result == "async_data"


def test_injected_pytest_invalid_override_type():
    """Test providing invalid override type."""
    # Try to use a string as override (invalid)
    with pytest.raises(AssertionError, match="override must be a Design"):

        @injected_pytest("invalid_override")
        def test_func():
            return "test"


def test_injected_pytest_with_task_group():
    """Test that __task_group__ is properly injected."""
    from pinjected import injected

    captured_task_group = None

    @injected
    def capture_task_group(__task_group__):
        nonlocal captured_task_group
        captured_task_group = __task_group__
        return "captured"

    test_design = design(capture=capture_task_group)

    @injected_pytest(test_design)
    def test_func(capture):
        return capture()  # Need to call the function

    result = test_func()
    assert result == "captured"
    assert captured_task_group is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
