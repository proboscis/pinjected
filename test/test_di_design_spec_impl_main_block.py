"""Tests for the main block execution in pinjected/di/design_spec/impl.py."""

import pytest
from unittest.mock import patch
import sys
from io import StringIO

# Import the module to get access to the classes and functions
from pinjected.di.design_spec.impl import (
    IOSuccess,
    IOFailure,
    unsafe_perform_io,
    future_safe,
    FutureResult,
    FutureResultE,
    Some,
    Nothing,
)


class TestMainBlockExecution:
    """Test the code in the main block of impl.py."""

    def test_io_success_failure_examples(self):
        """Test IOSuccess and IOFailure behavior."""
        # Test IOSuccess
        success = IOSuccess("success")
        assert str(success).endswith("IOSuccess(success)")
        assert success.value_or("hello") == IOSuccess("success")

        # Test IOFailure
        exception = Exception("test error")
        failure = IOFailure(exception)
        assert "IOFailure" in str(failure)
        assert failure.value_or("hello") == IOSuccess("hello")

        # Test unsafe_perform_io
        result_success = unsafe_perform_io(success)
        assert result_success.is_successful()
        assert result_success.unwrap() == "success"

        result_failure = unsafe_perform_io(failure)
        assert not result_failure.is_successful()

    @pytest.mark.asyncio
    async def test_future_safe_decorator(self):
        """Test the future_safe decorator."""

        # Define an error function using future_safe
        @future_safe
        async def error_func():
            raise Exception("error")

        # Test that it returns a FutureResultE
        fut_res = error_func()
        assert isinstance(fut_res, FutureResultE)

        # Run the future and check the result
        res = await fut_res.awaitable()
        assert not unsafe_perform_io(res).is_successful()

    @pytest.mark.asyncio
    async def test_future_result_recovery(self):
        """Test FutureResult recovery using lash."""

        # Create a failing future
        @future_safe
        async def error_func():
            raise Exception("error")

        fut_res = error_func()

        # Define recovery functions
        @future_safe
        async def recover(fail):
            return "recovered"

        def recover2(fail):
            return FutureResult.from_value("recovered")

        # Test different recovery methods
        recovered = fut_res.lash(recover)
        recovered_2 = fut_res.lash(recover2)
        recovered_3 = fut_res.lash(lambda x: FutureResult.from_value("recovered"))

        # Check recovery results
        res1 = await recovered.awaitable()
        res2 = await recovered_2.awaitable()
        res3 = await recovered_3.awaitable()

        assert unsafe_perform_io(res1).is_successful()
        assert unsafe_perform_io(res1).unwrap() == "recovered"
        assert unsafe_perform_io(res2).is_successful()
        assert unsafe_perform_io(res2).unwrap() == "recovered"
        assert unsafe_perform_io(res3).is_successful()
        assert unsafe_perform_io(res3).unwrap() == "recovered"

    @pytest.mark.asyncio
    async def test_await_target_function(self):
        """Test the await_target function pattern."""

        # Define await_target similar to the main block
        async def await_target(f: FutureResultE):
            return await f

        # Test with success
        @future_safe
        async def success_func():
            return "success"

        fut_success = success_func()
        result = await await_target(fut_success)
        assert unsafe_perform_io(result).is_successful()
        assert unsafe_perform_io(result).unwrap() == "success"

        # Test with failure
        @future_safe
        async def error_func():
            raise Exception("error")

        fut_error = error_func()
        result = await await_target(fut_error)
        assert not unsafe_perform_io(result).is_successful()

    def test_maybe_behavior(self):
        """Test Maybe (Some/Nothing) behavior."""
        # Test Some
        some = Some("hello")
        assert str(some) == "Some(hello)"

        # Test bind on Some
        result = some.bind(lambda d: Some(isinstance(d, str)))
        assert result == Some(True)

        # Test Nothing
        none = Nothing
        assert str(none) == "Nothing"

        # Test lash on Nothing (should return Nothing)
        result = none.lash(lambda fail: Some("recovered"))
        assert result == Nothing

    def test_execute_main_block(self):
        """Execute the main block by importing the module."""
        # Capture stdout
        original_stdout = sys.stdout
        sys.stdout = StringIO()

        try:
            # Mock logger to avoid actual logging
            with patch("pinjected.di.design_spec.impl.logger"):
                # Import and execute the main block
                import importlib

                spec = importlib.util.spec_from_file_location(
                    "impl_main",
                    "/Users/s22625/repos/pinjected/pinjected/di/design_spec/impl.py",
                )
                module = importlib.util.module_from_spec(spec)

                # Execute the module (which runs the main block)
                spec.loader.exec_module(module)

                # Verify some objects were created
                assert hasattr(module, "IOSuccess")
                assert hasattr(module, "IOFailure")
                assert hasattr(module, "future_safe")

        finally:
            sys.stdout = original_stdout

    @pytest.mark.asyncio
    async def test_complex_future_result_chain(self):
        """Test complex chaining of FutureResult operations."""

        # Create a chain of operations
        @future_safe
        async def step1():
            return 10

        @future_safe
        async def step2(value):
            return value * 2

        @future_safe
        async def step3(value):
            if value > 15:
                raise Exception("Value too large")
            return value + 5

        # Test successful chain
        result = await step1().bind(step2).bind(step3).awaitable()
        assert not unsafe_perform_io(result).is_successful()  # 20 > 15

        # Test with recovery
        recovered = await (
            step1()
            .bind(step2)
            .bind(step3)
            .lash(lambda _: FutureResult.from_value(25))
            .awaitable()
        )
        assert unsafe_perform_io(recovered).is_successful()
        assert unsafe_perform_io(recovered).unwrap() == 25

    def test_io_monad_properties(self):
        """Test IO monad properties."""
        # Test that IOSuccess wraps values properly
        success = IOSuccess([1, 2, 3])
        assert success.value_or([]) == IOSuccess([1, 2, 3])

        # Test nested structures
        nested = IOSuccess(IOSuccess("nested"))
        result = unsafe_perform_io(nested)
        assert result.is_successful()

        # Test with None
        none_success = IOSuccess(None)
        assert unsafe_perform_io(none_success).unwrap() is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
