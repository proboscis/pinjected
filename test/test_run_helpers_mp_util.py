"""Tests for run_helpers/mp_util.py module."""

import pytest
import asyncio
from unittest.mock import Mock, patch
from pinjected.run_helpers.mp_util import process_runner, FutureWithStd, run_in_process


def test_process_runner_success():
    """Test process_runner with successful function execution."""
    # Create a mock queue with put method
    result_queue = Mock()
    result_queue.put = Mock()

    # Define a simple function
    def test_func(x, y):
        return x + y

    # Run the process runner
    process_runner(test_func, (5, 3), result_queue)

    # Check that success result was put in queue
    result_queue.put.assert_called_once_with(("success", 8))


def test_process_runner_exception():
    """Test process_runner with function that raises exception."""
    # Create a mock queue with put method
    result_queue = Mock()
    result_queue.put = Mock()

    # Define a function that raises
    def failing_func():
        raise ValueError("Test error")

    # Run the process runner
    process_runner(failing_func, (), result_queue)

    # Check that error was put in queue
    result_queue.put.assert_called_once()
    call_args = result_queue.put.call_args[0][0]
    assert call_args[0] == "error"
    assert "Test error" in call_args[1]


@pytest.mark.asyncio
async def test_future_with_std_stream_stdout():
    """Test FutureWithStd streaming stdout."""
    # Create mock future and queues
    future = asyncio.Future()
    stdout_queue = asyncio.Queue()
    stderr_queue = asyncio.Queue()

    fws = FutureWithStd(
        result=future, stdout_queue=stdout_queue, stderr_queue=stderr_queue
    )

    # Put some data in stdout queue
    await stdout_queue.put(("data", "line 1"))
    await stdout_queue.put(("data", "line 2"))
    await stdout_queue.put(("end", None))

    # Stream stdout
    lines = []
    async for line in fws.stream_stdout():
        lines.append(line)

    assert lines == ["line 1", "line 2"]


@pytest.mark.asyncio
async def test_future_with_std_stream_stderr():
    """Test FutureWithStd streaming stderr."""
    # Create mock future and queues
    future = asyncio.Future()
    stdout_queue = asyncio.Queue()
    stderr_queue = asyncio.Queue()

    fws = FutureWithStd(
        result=future, stdout_queue=stdout_queue, stderr_queue=stderr_queue
    )

    # Put some data in stderr queue
    await stderr_queue.put(("data", "error 1"))
    await stderr_queue.put(("data", "error 2"))
    await stderr_queue.put(("end", None))

    # Stream stderr
    errors = []
    async for error in fws.stream_stderr():
        errors.append(error)

    assert errors == ["error 1", "error 2"]


@pytest.mark.asyncio
async def test_run_in_process_success():
    """Test run_in_process with successful function."""

    # Define a simple function to run
    def add_numbers(x, y):
        return x + y

    # Mock multiprocessing components
    with (
        patch(
            "pinjected.run_helpers.mp_util.multiprocessing.Queue"
        ) as mock_queue_class,
        patch(
            "pinjected.run_helpers.mp_util.multiprocessing.Process"
        ) as mock_process_class,
    ):
        # Set up mock queue
        mock_queue = Mock()
        # Queue is empty while process runs, then has result after process dies
        # The check after the loop needs to see non-empty queue
        mock_queue.empty.side_effect = [True, True, False]
        mock_queue.get.return_value = ("success", 42)
        mock_queue_class.return_value = mock_queue

        # Set up mock process
        mock_process = Mock()
        # Process is alive for two checks, then dies
        mock_process.is_alive.side_effect = [True, True, False]
        mock_process_class.return_value = mock_process

        # Mock sleep to avoid actual waiting
        with patch("pinjected.run_helpers.mp_util.asyncio.sleep"):
            # Run the function
            result = await run_in_process(add_numbers, 20, 22)

        # Verify behavior
        assert result == 42
        mock_process.start.assert_called_once()
        mock_queue.get.assert_called_once()


@pytest.mark.asyncio
async def test_run_in_process_error():
    """Test run_in_process with function that raises exception."""

    # Define a failing function
    def failing_func():
        raise ValueError("Test error")

    # Mock multiprocessing components
    with (
        patch(
            "pinjected.run_helpers.mp_util.multiprocessing.Queue"
        ) as mock_queue_class,
        patch(
            "pinjected.run_helpers.mp_util.multiprocessing.Process"
        ) as mock_process_class,
    ):
        # Set up mock queue
        mock_queue = Mock()
        # Queue is empty while process runs, then has result after process dies
        # The check after the loop needs to see non-empty queue
        mock_queue.empty.side_effect = [True, True, False]
        mock_queue.get.return_value = (
            "error",
            "Function raised an exception: Test error",
        )
        mock_queue_class.return_value = mock_queue

        # Set up mock process
        mock_process = Mock()
        # Process is alive for two checks, then dies
        mock_process.is_alive.side_effect = [True, True, False]
        mock_process_class.return_value = mock_process

        # Mock sleep to avoid actual waiting
        with (
            patch("pinjected.run_helpers.mp_util.asyncio.sleep"),
            pytest.raises(RuntimeError, match="Function raised an exception"),
        ):
            await run_in_process(failing_func)


@pytest.mark.asyncio
async def test_run_in_process_no_result():
    """Test run_in_process when process ends without result."""

    # Define a function
    def some_func():
        return "value"

    # Mock multiprocessing components
    with (
        patch(
            "pinjected.run_helpers.mp_util.multiprocessing.Queue"
        ) as mock_queue_class,
        patch(
            "pinjected.run_helpers.mp_util.multiprocessing.Process"
        ) as mock_process_class,
    ):
        # Set up mock queue that stays empty
        mock_queue = Mock()
        mock_queue.empty.return_value = True
        mock_queue_class.return_value = mock_queue

        # Set up mock process that's not alive
        mock_process = Mock()
        mock_process.is_alive.return_value = False
        mock_process_class.return_value = mock_process

        # Run the function and expect error
        with pytest.raises(
            RuntimeError, match="Process ended without returning a result"
        ):
            await run_in_process(some_func)


@pytest.mark.asyncio
async def test_run_in_process_wait_for_result():
    """Test run_in_process waits for result."""

    # Define a function
    def slow_func():
        return "slow_result"

    # Mock multiprocessing components
    with (
        patch(
            "pinjected.run_helpers.mp_util.multiprocessing.Queue"
        ) as mock_queue_class,
        patch(
            "pinjected.run_helpers.mp_util.multiprocessing.Process"
        ) as mock_process_class,
        patch("pinjected.run_helpers.mp_util.asyncio.sleep") as mock_sleep,
    ):
        # Set up mock queue
        mock_queue = Mock()
        # Empty for first few checks, then has result
        mock_queue.empty.side_effect = [True, True, True, False]
        mock_queue.get.return_value = ("success", "slow_result")
        mock_queue_class.return_value = mock_queue

        # Set up mock process that stays alive for a bit
        mock_process = Mock()
        mock_process.is_alive.side_effect = [True, True, True, False]
        mock_process_class.return_value = mock_process

        # Run the function
        result = await run_in_process(slow_func)

        # Verify behavior
        assert result == "slow_result"
        assert mock_sleep.call_count == 3  # Should have slept 3 times


def test_future_with_std_dataclass():
    """Test FutureWithStd dataclass creation."""
    # Create event loop for asyncio objects
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        future = asyncio.Future()
        stdout_q = asyncio.Queue()
        stderr_q = asyncio.Queue()

        fws = FutureWithStd(result=future, stdout_queue=stdout_q, stderr_queue=stderr_q)

        assert fws.result is future
        assert fws.stdout_queue is stdout_q
        assert fws.stderr_queue is stderr_q
    finally:
        loop.close()
        asyncio.set_event_loop(None)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
