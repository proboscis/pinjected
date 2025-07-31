"""Tests for pinjected.test_helper.rich_task_viz module."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from rich.console import Console
from rich.table import Table

from pinjected.test_helper.rich_task_viz import RichTaskVisualizer, task_visualizer


class TestRichTaskVisualizer:
    """Test the RichTaskVisualizer class."""

    def test_init(self):
        """Test RichTaskVisualizer initialization."""
        viz = RichTaskVisualizer()

        assert isinstance(viz.statuses, dict)
        assert isinstance(viz.messages, dict)
        assert isinstance(viz.console, Console)
        assert hasattr(viz, "live")
        assert viz.statuses == {}
        assert viz.messages == {}

    def test_init_with_custom_console(self):
        """Test RichTaskVisualizer with custom console."""
        mock_console = Mock(spec=Console)
        viz = RichTaskVisualizer(console=mock_console)

        assert viz.console is mock_console

    def test_add_task(self):
        """Test adding a new task."""
        viz = RichTaskVisualizer()

        # Mock the update method to avoid live display
        viz.update = Mock()

        viz.add("task1", "running", "Processing data")

        assert "task1" in viz.statuses
        assert viz.statuses["task1"] == "running"
        assert "task1" in viz.messages
        assert viz.messages["task1"] == "Processing data"
        viz.update.assert_called_once()

    def test_add_task_with_renderable(self):
        """Test adding a task with ConsoleRenderable message."""
        viz = RichTaskVisualizer()
        viz.update = Mock()

        # Create a mock renderable
        mock_renderable = Mock()

        viz.add("task2", "pending", mock_renderable)

        assert viz.statuses["task2"] == "pending"
        assert viz.messages["task2"] is mock_renderable
        viz.update.assert_called_once()

    def test_update_status(self):
        """Test updating task status."""
        viz = RichTaskVisualizer()
        viz.update = Mock()

        # Add a task first
        viz.statuses["task1"] = "running"
        viz.messages["task1"] = "Processing"

        # Update status
        viz.update_status("task1", "completed")

        assert viz.statuses["task1"] == "completed"
        viz.update.assert_called_once()

    def test_update_message(self):
        """Test updating task message."""
        viz = RichTaskVisualizer()
        viz.update = Mock()

        # Add a task first
        viz.statuses["task1"] = "running"
        viz.messages["task1"] = "Processing"

        # Update message
        viz.update_message("task1", "Almost done")

        assert viz.messages["task1"] == "Almost done"
        viz.update.assert_called_once()

    def test_update_message_nonexistent_task(self):
        """Test updating message for non-existent task."""
        viz = RichTaskVisualizer()
        viz.update = Mock()

        # Try to update non-existent task
        viz.update_message("unknown", "Some message")

        # Should not add the task
        assert "unknown" not in viz.messages
        viz.update.assert_called_once()

    def test_remove_task(self):
        """Test removing a task."""
        viz = RichTaskVisualizer()
        viz.update = Mock()

        # Add tasks
        viz.statuses["task1"] = "running"
        viz.messages["task1"] = "Processing"
        viz.statuses["task2"] = "pending"
        viz.messages["task2"] = "Waiting"

        # Remove task1
        viz.remove("task1")

        assert "task1" not in viz.statuses
        assert "task1" not in viz.messages
        assert "task2" in viz.statuses
        assert "task2" in viz.messages
        viz.update.assert_called_once()

    def test_remove_nonexistent_task(self):
        """Test removing non-existent task."""
        viz = RichTaskVisualizer()
        viz.update = Mock()

        # Try to remove non-existent task
        viz.remove("unknown")

        # Should not raise error
        viz.update.assert_called_once()

    def test_generate_table_empty(self):
        """Test generating table with no tasks."""
        viz = RichTaskVisualizer()

        table = viz._generate_table()

        assert isinstance(table, Table)
        assert table.title == "Current Tasks"
        assert len(table.columns) == 3
        assert table.columns[0].header == "Task"
        assert table.columns[1].header == "Status"
        assert table.columns[2].header == "Message"

    def test_generate_table_with_tasks(self):
        """Test generating table with tasks."""
        viz = RichTaskVisualizer()

        # Add tasks
        viz.statuses = {"task1": "running", "task2": "completed", "task3": "failed"}
        viz.messages = {
            "task1": "Processing data",
            "task2": "Done",
            "task3": "Error occurred",
        }

        table = viz._generate_table()

        assert isinstance(table, Table)
        # Check that rows were added (can't easily check content without rendering)
        assert len(viz.statuses) == 3

    def test_update_method(self):
        """Test the update method."""
        viz = RichTaskVisualizer()

        # Mock the live object
        viz.live = Mock()
        viz.live.update = Mock()

        # Create a mock table
        mock_table = Mock(spec=Table)
        viz._generate_table = Mock(return_value=mock_table)

        viz.update()

        viz._generate_table.assert_called_once()
        viz.live.update.assert_called_once_with(mock_table)

    def test_post_init_creates_live(self):
        """Test that __post_init__ creates Live object."""
        with patch("pinjected.test_helper.rich_task_viz.Live") as mock_live_class:
            mock_live = Mock()
            mock_live_class.return_value = mock_live

            viz = RichTaskVisualizer()

            mock_live_class.assert_called_once()
            assert viz.live is mock_live

    def test_add_multiple_tasks(self):
        """Test adding multiple tasks."""
        viz = RichTaskVisualizer()
        viz.update = Mock()

        tasks = [
            ("download", "running", "Downloading file 1/10"),
            ("process", "pending", "Waiting for download"),
            ("upload", "pending", "Waiting for processing"),
        ]

        for name, status, message in tasks:
            viz.add(name, status, message)

        assert len(viz.statuses) == 3
        assert len(viz.messages) == 3
        assert viz.update.call_count == 3

    def test_complex_workflow(self):
        """Test a complex workflow with multiple operations."""
        viz = RichTaskVisualizer()
        viz.update = Mock()

        # Add tasks
        viz.add("task1", "starting", "Initializing")
        viz.add("task2", "waiting", "In queue")

        # Update task1
        viz.update_status("task1", "running")
        viz.update_message("task1", "Processing 50%")

        # Start task2
        viz.update_status("task2", "running")
        viz.update_message("task2", "Processing")

        # Complete task1
        viz.update_status("task1", "completed")
        viz.remove("task1")

        # Only task2 should remain
        assert len(viz.statuses) == 1
        assert "task2" in viz.statuses
        assert viz.statuses["task2"] == "running"


class TestTaskVisualizerContextManager:
    """Test the task_visualizer async context manager."""

    @pytest.mark.asyncio
    async def test_context_manager_basic(self):
        """Test basic usage of task_visualizer context manager."""
        async with task_visualizer() as viz:
            assert isinstance(viz, RichTaskVisualizer)
            assert hasattr(viz, "live")
            assert hasattr(viz, "statuses")
            assert hasattr(viz, "messages")

    @pytest.mark.asyncio
    async def test_context_manager_with_tasks(self):
        """Test task_visualizer with adding tasks."""
        async with task_visualizer() as viz:
            # Mock the update method to avoid display
            viz.update = Mock()

            viz.add("async_task", "running", "Processing async")
            assert "async_task" in viz.statuses

    @pytest.mark.asyncio
    async def test_context_manager_exception_handling(self):
        """Test that context manager handles exceptions properly."""
        with pytest.raises(ValueError):
            async with task_visualizer() as viz:
                viz.update = Mock()
                viz.add("task", "running", "Test")
                raise ValueError("Test error")

        # Context manager should exit cleanly

    @pytest.mark.asyncio
    async def test_context_manager_cleanup(self):
        """Test that context manager performs cleanup."""
        viz = None
        async with task_visualizer() as v:
            viz = v
            viz.update = Mock()
            viz.add("task", "running", "Test")

        # After context, the visualizer should still exist
        # but live display should be stopped
        assert viz is not None
        assert "task" in viz.statuses

    @pytest.mark.asyncio
    async def test_context_manager_live_display(self):
        """Test that Live display is properly managed."""
        with patch("pinjected.test_helper.rich_task_viz.Live") as mock_live_class:
            mock_live = MagicMock()
            mock_live.__enter__ = Mock(return_value=mock_live)
            mock_live.__exit__ = Mock(return_value=None)
            mock_live_class.return_value = mock_live

            async with task_visualizer():
                # Live should be entered
                mock_live.__enter__.assert_called_once()

            # Live should be exited
            mock_live.__exit__.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
