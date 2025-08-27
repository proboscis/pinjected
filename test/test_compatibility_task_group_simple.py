"""Simple tests for compatibility/task_group.py module."""

import pytest
import asyncio
import sys
from unittest.mock import patch

from pinjected.compatibility import task_group


class TestCompatibilityTaskGroup:
    """Test the compatibility task_group module functionality."""

    def test_exception_group_class(self):
        """Test the ExceptionGroup class."""
        exceptions = [ValueError("error1"), TypeError("error2")]
        exc_group = task_group.ExceptionGroup(exceptions)

        assert exc_group.exceptions == exceptions
        assert isinstance(exc_group, Exception)

    def test_compatible_exception_group_alias(self):
        """Test that CompatibleExceptionGroup is an alias for ExceptionGroup."""
        assert task_group.CompatibleExceptionGroup is task_group.ExceptionGroup

    @pytest.mark.skipif(
        sys.version_info >= (3, 11),
        reason="Custom TaskGroup only used in Python < 3.11",
    )
    def test_custom_task_group_basic(self):
        """Test custom TaskGroup implementation for Python < 3.11."""
        # Force import of custom TaskGroup
        with patch.dict("sys.modules", {"asyncio.TaskGroup": None}):
            # Re-import to trigger the ImportError path
            import importlib

            importlib.reload(task_group)

            tg = task_group.TaskGroup()
            assert tg.tasks == []

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        sys.version_info >= (3, 11),
        reason="Custom TaskGroup only used in Python < 3.11",
    )
    async def test_custom_task_group_create_task(self):
        """Test create_task method of custom TaskGroup."""

        async def sample_task():
            await asyncio.sleep(0.01)
            return "done"

        # Force use of custom TaskGroup
        tg = task_group.TaskGroup()
        task = tg.create_task(sample_task())

        assert len(tg.tasks) == 1
        assert asyncio.iscoroutine(task.get_coro()) or asyncio.isfuture(task)

        result = await task
        assert result == "done"

    @pytest.mark.asyncio
    async def test_task_group_context_manager(self):
        """Test TaskGroup as async context manager."""
        results = []

        async def task1():
            await asyncio.sleep(0.01)
            results.append(1)

        async def task2():
            await asyncio.sleep(0.01)
            results.append(2)

        async with task_group.TaskGroup() as tg:
            tg.create_task(task1())
            tg.create_task(task2())

        assert len(results) == 2
        assert 1 in results
        assert 2 in results

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        sys.version_info >= (3, 11),
        reason="Custom TaskGroup only used in Python < 3.11",
    )
    async def test_custom_task_group_exception_handling(self):
        """Test exception handling in custom TaskGroup."""

        async def failing_task():
            await asyncio.sleep(0.01)
            raise ValueError("task failed")

        # Force use of custom TaskGroup
        tg = task_group.TaskGroup()

        with pytest.raises(task_group.ExceptionGroup) as exc_info:
            async with tg:
                tg.create_task(failing_task())

        assert len(exc_info.value.exceptions) == 1
        assert isinstance(exc_info.value.exceptions[0], ValueError)

    @pytest.mark.skipif(
        sys.version_info >= (3, 11),
        reason="Custom TaskGroup only used in Python < 3.11",
    )
    def test_import_warning_logged(self):
        """Test that warning is logged when using custom TaskGroup."""
        with (
            patch("pinjected.compatibility.task_group.logger") as mock_logger,
            patch(
                "pinjected.compatibility.task_group.multiprocessing.current_process"
            ) as mock_process,
        ):
            # Mock process to not be SpawnProcess
            mock_process.return_value.name = "MainProcess"

            # Force reimport to trigger warning
            with patch.dict("sys.modules", {"asyncio.TaskGroup": None}):
                import importlib

                importlib.reload(task_group)

            # Check warning was logged
            mock_logger.warning.assert_called()
            warning_msg = mock_logger.warning.call_args[0][0]
            assert "Using compatibility.task_group.TaskGroup" in warning_msg

    def test_module_has_task_group(self):
        """Test that module exports TaskGroup."""
        assert hasattr(task_group, "TaskGroup")

    @pytest.mark.asyncio
    async def test_multiple_tasks_success(self):
        """Test TaskGroup with multiple successful tasks."""
        results = []

        async def append_value(value, delay=0.01):
            await asyncio.sleep(delay)
            results.append(value)
            return value

        async with task_group.TaskGroup() as tg:
            t1 = tg.create_task(append_value(1))
            t2 = tg.create_task(append_value(2))
            t3 = tg.create_task(append_value(3))

        assert results == [1, 2, 3] or set(results) == {1, 2, 3}  # Order may vary
        assert await t1 == 1
        assert await t2 == 2
        assert await t3 == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
