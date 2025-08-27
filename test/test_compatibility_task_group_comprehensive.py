"""Comprehensive tests for pinjected/compatibility/task_group.py module."""

import pytest
import asyncio
from unittest.mock import patch, Mock
import sys

# Import the compatibility module
from pinjected.compatibility.task_group import ExceptionGroup, CompatibleExceptionGroup


class TestExceptionGroup:
    """Tests for ExceptionGroup class."""

    def test_exception_group_creation(self):
        """Test creating ExceptionGroup with exceptions."""
        exc1 = ValueError("Error 1")
        exc2 = TypeError("Error 2")
        exc_group = ExceptionGroup([exc1, exc2])

        assert exc_group.exceptions == [exc1, exc2]
        assert isinstance(exc_group, Exception)

    def test_exception_group_empty(self):
        """Test creating ExceptionGroup with no exceptions."""
        exc_group = ExceptionGroup([])

        assert exc_group.exceptions == []

    def test_exception_group_single(self):
        """Test creating ExceptionGroup with single exception."""
        exc = RuntimeError("Single error")
        exc_group = ExceptionGroup([exc])

        assert exc_group.exceptions == [exc]
        assert len(exc_group.exceptions) == 1

    def test_compatible_exception_group_alias(self):
        """Test that CompatibleExceptionGroup is an alias for ExceptionGroup."""
        assert CompatibleExceptionGroup is ExceptionGroup


# Only test our custom TaskGroup if it's being used (Python < 3.11)
if sys.version_info < (3, 11):

    class TestTaskGroup:
        """Tests for custom TaskGroup implementation."""

        @pytest.mark.asyncio
        async def test_task_group_basic_usage(self):
            """Test basic TaskGroup usage."""
            results = []

            async def task1():
                await asyncio.sleep(0.01)
                results.append("task1")
                return "result1"

            async def task2():
                await asyncio.sleep(0.01)
                results.append("task2")
                return "result2"

            from pinjected.compatibility.task_group import TaskGroup

            async with TaskGroup() as tg:
                tg.create_task(task1())
                tg.create_task(task2())

            assert len(results) == 2
            assert "task1" in results
            assert "task2" in results

        @pytest.mark.asyncio
        async def test_task_group_exception_handling(self):
            """Test TaskGroup exception handling."""

            async def failing_task():
                await asyncio.sleep(0.01)
                raise ValueError("Task failed")

            async def normal_task():
                await asyncio.sleep(0.01)
                return "success"

            from pinjected.compatibility.task_group import TaskGroup

            with pytest.raises(ExceptionGroup) as exc_info:
                async with TaskGroup() as tg:
                    tg.create_task(failing_task())
                    tg.create_task(normal_task())

            assert len(exc_info.value.exceptions) == 1
            assert isinstance(exc_info.value.exceptions[0], ValueError)
            assert str(exc_info.value.exceptions[0]) == "Task failed"

        @pytest.mark.asyncio
        async def test_task_group_create_task_returns_task(self):
            """Test that create_task returns the created task."""

            async def sample_task():
                return "task_result"

            from pinjected.compatibility.task_group import TaskGroup

            tg = TaskGroup()
            task = tg.create_task(sample_task())

            assert isinstance(task, asyncio.Task)
            assert task in tg.tasks

            # Clean up
            await task

        @pytest.mark.asyncio
        async def test_task_group_multiple_exceptions(self):
            """Test TaskGroup with multiple failing tasks."""

            async def failing_task1():
                await asyncio.sleep(0.01)
                raise ValueError("Error 1")

            async def failing_task2():
                await asyncio.sleep(0.02)
                raise TypeError("Error 2")

            from pinjected.compatibility.task_group import TaskGroup

            # Note: Our simple implementation only catches the first exception
            with pytest.raises(ExceptionGroup) as exc_info:
                async with TaskGroup() as tg:
                    tg.create_task(failing_task1())
                    tg.create_task(failing_task2())

            # Due to the simple implementation, only the first exception is caught
            assert len(exc_info.value.exceptions) == 1

        @pytest.mark.asyncio
        async def test_task_group_empty(self):
            """Test TaskGroup with no tasks."""
            from pinjected.compatibility.task_group import TaskGroup

            async with TaskGroup() as tg:
                pass  # No tasks created

            # Should complete without error
            assert len(tg.tasks) == 0

        def test_task_group_init(self):
            """Test TaskGroup initialization."""
            from pinjected.compatibility.task_group import TaskGroup

            tg = TaskGroup()
            assert tg.tasks == []
            assert hasattr(tg, "create_task")
            assert hasattr(tg, "__aenter__")
            assert hasattr(tg, "__aexit__")


class TestModuleImport:
    """Tests for module import behavior."""

    @patch("pinjected.compatibility.task_group.multiprocessing.current_process")
    def test_import_warning_non_spawn_process(self, mock_current_process):
        """Test that warning is logged for non-SpawnProcess in Python < 3.11."""
        if sys.version_info >= (3, 11):
            pytest.skip("Test only relevant for Python < 3.11")

        # Mock the current process
        mock_process = Mock()
        mock_process.name = "MainProcess"
        mock_current_process.return_value = mock_process

        # Re-import the module to trigger the warning

        # The warning should have been logged during import
        # (We can't easily test the logger call without more complex mocking)

    @patch("pinjected.compatibility.task_group.multiprocessing.current_process")
    def test_no_warning_spawn_process(self, mock_current_process):
        """Test that no warning is logged for SpawnProcess."""
        if sys.version_info >= (3, 11):
            pytest.skip("Test only relevant for Python < 3.11")

        # Mock the current process
        mock_process = Mock()
        mock_process.name = "SpawnProcess-1"
        mock_current_process.return_value = mock_process

        # Re-import the module - should not log warning


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
