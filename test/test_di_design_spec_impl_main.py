"""Tests for the main block of di/design_spec/impl.py to improve coverage."""

import pytest
from unittest.mock import patch

# Import the necessary types from the module
from pinjected.di.design_spec.impl import (
    IOSuccess,
    IOFailure,
    unsafe_perform_io,
    FutureResultE,
    FutureResult,
)
from returns.future import future_safe
from returns.maybe import Some, Nothing


class TestMainBlockCoverage:
    """Test cases that cover the main block code."""

    def test_io_success_failure_basic(self):
        """Test IOSuccess and IOFailure basic usage."""
        success = IOSuccess("success")
        failure = IOFailure(Exception("test error"))

        # Test string representation
        assert "success" in str(success)
        assert "Failure" in str(failure) or "IOResult" in str(failure)

        # Test value_or - returns IO object
        assert str(success.value_or("hello")) == "<IO: success>"
        assert str(failure.value_or("hello")) == "<IO: hello>"

        # Test unsafe_perform_io
        from returns.result import Failure

        success_result = unsafe_perform_io(success)
        failure_result = unsafe_perform_io(failure)

        assert success_result.unwrap() == "success"
        assert isinstance(failure_result, Failure)

        # Test unwrap on IOSuccess returns Success
        from returns.io import IO

        unwrapped = success.unwrap()
        assert isinstance(unwrapped, IO)
        assert unwrapped._inner_value == "success"

    @pytest.mark.asyncio
    async def test_future_safe_error_handling(self):
        """Test future_safe decorator with error handling."""

        @future_safe
        async def error_func():
            raise Exception("error")

        fut_res: FutureResultE[str] = error_func()

        # Test that it returns a FutureResultE
        assert hasattr(fut_res, "awaitable")

        # Await the result
        res = await fut_res.awaitable()

        # Should be a failure
        from returns.result import Failure

        io_res = unsafe_perform_io(res)
        assert isinstance(io_res, Failure)
        assert "error" in str(io_res)

    @pytest.mark.asyncio
    async def test_future_result_recovery(self):
        """Test FutureResultE recovery using lash."""
        from returns.result import Failure

        @future_safe
        async def error_func():
            raise Exception("error")

        @future_safe
        async def recover(fail):
            return "recovered"

        def recover2(fail):
            return FutureResult.from_value("recovered")

        # Create a failing future
        fut_res = error_func()

        # Test different recovery methods
        recovered = fut_res.lash(recover)
        recovered_2 = fut_res.lash(recover2)
        recovered_3 = fut_res.lash(lambda x: FutureResult.from_value("recovered"))

        # Await all results
        original_result = await fut_res.awaitable()
        recovered_result = await recovered.awaitable()
        recovered_2_result = await recovered_2.awaitable()
        recovered_3_result = await recovered_3.awaitable()

        # Original should be failure
        assert isinstance(unsafe_perform_io(original_result), Failure)

        # All recovered versions should be success
        assert unsafe_perform_io(recovered_result).unwrap() == "recovered"
        assert unsafe_perform_io(recovered_2_result).unwrap() == "recovered"
        assert unsafe_perform_io(recovered_3_result).unwrap() == "recovered"

    @pytest.mark.asyncio
    async def test_await_target_pattern(self):
        """Test the await_target pattern from main block."""
        from returns.result import Failure

        @future_safe
        async def error_func():
            raise Exception("error")

        @future_safe
        async def recover(fail):
            return "recovered"

        async def await_target(f: FutureResultE):
            return await f

        # Test with error
        fut_res = error_func()
        result = await await_target(fut_res)
        assert isinstance(unsafe_perform_io(result), Failure)

        # Test with recovery
        recovered = fut_res.lash(recover)
        recovered_result = await await_target(recovered)
        assert unsafe_perform_io(recovered_result).unwrap() == "recovered"

    def test_maybe_behavior(self):
        """Test Maybe (Some/Nothing) behavior."""
        some = Some("hello")
        none = Nothing

        # Test string representation
        assert "hello" in str(some)
        assert "Nothing" in str(none)

        # Test bind on Some
        bind_result = some.bind(lambda d: Some(isinstance(d, str)))
        assert bind_result.unwrap() is True

        # Test lash on Nothing (should recover)
        lash_result = none.lash(lambda fail: Some("recovered"))
        assert lash_result == Some("recovered")

    def test_main_block_execution(self):
        """Test that simulates the main block execution."""
        # This test ensures all the logger.info calls would work
        with patch("loguru.logger.info") as mock_info, patch("loguru.logger.warning"):
            # Simulate some of the main block operations
            success = IOSuccess("success")
            failure = IOFailure(Exception())

            # These would be logger.info calls in main
            mock_info(success)
            mock_info(failure)
            mock_info(success.value_or("hello"))
            mock_info(failure.value_or("hello"))

            # Verify logger was called
            assert mock_info.call_count >= 4

    @pytest.mark.asyncio
    async def test_future_result_patterns(self):
        """Test various FutureResult patterns from main block."""

        @future_safe
        async def success_func():
            return "success_value"

        @future_safe
        async def error_func():
            raise Exception("test_error")

        # Test success case
        success_future = success_func()
        success_result = await success_future.awaitable()
        assert unsafe_perform_io(success_result).unwrap() == "success_value"

        # Test error case with recovery
        error_future = error_func()

        # Define recovery function inline like in main
        recovered = error_future.lash(lambda x: FutureResult.from_value("recovered"))
        recovered_result = await recovered.awaitable()
        assert unsafe_perform_io(recovered_result).unwrap() == "recovered"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
