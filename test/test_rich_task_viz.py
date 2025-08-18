"""Tests for pinjected/test_helper/rich_task_viz.py module."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from rich.table import Table
from rich.console import Console

from pinjected.test_helper.rich_task_viz import RichTaskVisualizer, task_visualizer


class TestRichTaskVisualizer:
    """Tests for RichTaskVisualizer class."""

    @patch("pinjected.test_helper.rich_task_viz.Live")
    def test_init(self, mock_live_class):
        """Test RichTaskVisualizer initialization."""
        visualizer = RichTaskVisualizer()

        # Check initial state
        assert visualizer.statuses == {}
        assert visualizer.messages == {}
        assert isinstance(visualizer.console, Console)

        # Check Live was created with correct parameters
        mock_live_class.assert_called_once()
        args, kwargs = mock_live_class.call_args
        assert isinstance(kwargs["console"], Console)
        assert kwargs["refresh_per_second"] == 8
        # First arg should be a table
        assert hasattr(args[0], "add_column")

    @patch("pinjected.test_helper.rich_task_viz.Live")
    def test_add(self, mock_live_class):
        """Test adding a new task."""
        mock_live = Mock()
        mock_live_class.return_value = mock_live

        visualizer = RichTaskVisualizer()
        visualizer.add("task1", "running", "Processing data")

        assert visualizer.statuses["task1"] == "running"
        assert visualizer.messages["task1"] == "Processing data"

        # Check that update was called
        assert mock_live.update.called

    @patch("pinjected.test_helper.rich_task_viz.Live")
    def test_update_status(self, mock_live_class):
        """Test updating task status."""
        mock_live = Mock()
        mock_live_class.return_value = mock_live

        visualizer = RichTaskVisualizer()
        visualizer.add("task1", "running", "Processing")

        # Update status
        visualizer.update_status("task1", "completed")

        assert visualizer.statuses["task1"] == "completed"
        assert visualizer.messages["task1"] == "Processing"  # Message unchanged

        # Check update was called
        assert mock_live.update.call_count >= 2  # Once for add, once for update_status

    @patch("pinjected.test_helper.rich_task_viz.Live")
    def test_remove(self, mock_live_class):
        """Test removing a task."""
        mock_live = Mock()
        mock_live_class.return_value = mock_live

        visualizer = RichTaskVisualizer()
        visualizer.add("task1", "running", "Processing")
        visualizer.add("task2", "pending", "Waiting")

        # Remove task1
        visualizer.remove("task1")

        assert "task1" not in visualizer.statuses
        assert "task1" not in visualizer.messages
        assert "task2" in visualizer.statuses
        assert "task2" in visualizer.messages

        # Test removing non-existent task (should not raise)
        visualizer.remove("non_existent")

    @patch("pinjected.test_helper.rich_task_viz.Live")
    def test_update_message(self, mock_live_class):
        """Test updating task message."""
        mock_live = Mock()
        mock_live_class.return_value = mock_live

        visualizer = RichTaskVisualizer()
        visualizer.add("task1", "running", "Processing")

        # Update message for existing task
        visualizer.update_message("task1", "Processing 50%")

        assert visualizer.messages["task1"] == "Processing 50%"
        assert visualizer.statuses["task1"] == "running"  # Status unchanged

        # Update message for non-existent task (should not add it)
        visualizer.update_message("non_existent", "Should not appear")
        assert "non_existent" not in visualizer.messages
        assert "non_existent" not in visualizer.statuses

    @patch("pinjected.test_helper.rich_task_viz.Live")
    def test_generate_table(self, mock_live_class):
        """Test table generation."""
        visualizer = RichTaskVisualizer()
        visualizer.add("task1", "running", "Processing data")
        visualizer.add("task2", "completed", "Done!")

        table = visualizer._generate_table()

        # Check table properties
        assert isinstance(table, Table)
        assert table.title == "Current Tasks"

        # Check columns were added
        assert len(table.columns) == 3
        assert table.columns[0].header == "Task"
        assert table.columns[1].header == "Status"
        assert table.columns[2].header == "Message"

    @patch("pinjected.test_helper.rich_task_viz.Live")
    def test_update(self, mock_live_class):
        """Test update method."""
        mock_live = Mock()
        mock_live_class.return_value = mock_live

        visualizer = RichTaskVisualizer()
        visualizer.update()

        # Check that live.update was called with a table
        mock_live.update.assert_called()
        args = mock_live.update.call_args[0]
        assert isinstance(args[0], Table)

    @patch("pinjected.test_helper.rich_task_viz.Live")
    def test_with_custom_console(self, mock_live_class):
        """Test creating visualizer with custom console."""
        custom_console = Mock(spec=Console)

        visualizer = RichTaskVisualizer(console=custom_console)

        assert visualizer.console == custom_console

        # Check Live was created with custom console
        _, kwargs = mock_live_class.call_args
        assert kwargs["console"] == custom_console

    @patch("pinjected.test_helper.rich_task_viz.Live")
    def test_multiple_operations(self, mock_live_class):
        """Test multiple operations in sequence."""
        mock_live = Mock()
        mock_live_class.return_value = mock_live

        visualizer = RichTaskVisualizer()

        # Add multiple tasks
        visualizer.add("download", "running", "Downloading file...")
        visualizer.add("process", "pending", "Waiting to process")
        visualizer.add("upload", "pending", "Waiting to upload")

        # Update some statuses
        visualizer.update_status("download", "completed")
        visualizer.update_status("process", "running")
        visualizer.update_message("process", "Processing 25%")

        # Remove completed task
        visualizer.remove("download")

        # Final state check
        assert len(visualizer.statuses) == 2
        assert visualizer.statuses["process"] == "running"
        assert visualizer.messages["process"] == "Processing 25%"
        assert visualizer.statuses["upload"] == "pending"

    @patch("pinjected.test_helper.rich_task_viz.Live")
    def test_console_renderable_support(self, mock_live_class):
        """Test support for ConsoleRenderable objects."""
        from rich.text import Text
        from rich.panel import Panel

        visualizer = RichTaskVisualizer()

        # Add with ConsoleRenderable objects
        status_text = Text("ACTIVE", style="bold red")
        message_panel = Panel("Complex message")

        visualizer.add("fancy_task", status_text, message_panel)

        assert visualizer.statuses["fancy_task"] == status_text
        assert visualizer.messages["fancy_task"] == message_panel


class TestTaskVisualizer:
    """Tests for task_visualizer async context manager."""

    @pytest.mark.asyncio
    @patch("pinjected.test_helper.rich_task_viz.RichTaskVisualizer")
    async def test_task_visualizer_context_manager(self, mock_visualizer_class):
        """Test basic usage of task_visualizer context manager."""
        mock_visualizer = Mock()
        mock_live = MagicMock()
        mock_visualizer.live = mock_live
        mock_visualizer_class.return_value = mock_visualizer

        # Use the context manager
        async with task_visualizer() as viz:
            assert viz == mock_visualizer
            # Check that live context was entered
            mock_live.__enter__.assert_called_once()

        # Check that live context was exited
        mock_live.__exit__.assert_called_once()

    @pytest.mark.asyncio
    @patch("pinjected.test_helper.rich_task_viz.RichTaskVisualizer")
    async def test_task_visualizer_with_exception(self, mock_visualizer_class):
        """Test task_visualizer handles exceptions properly."""
        mock_visualizer = Mock()
        mock_live = MagicMock()
        mock_visualizer.live = mock_live
        mock_visualizer_class.return_value = mock_visualizer

        # Test exception handling
        with pytest.raises(ValueError):
            async with task_visualizer():
                raise ValueError("Test error")

        # Check that live context was still exited properly
        mock_live.__exit__.assert_called_once()

    @pytest.mark.asyncio
    async def test_task_visualizer_integration(self):
        """Integration test for task_visualizer."""
        async with task_visualizer() as viz:
            # Test basic operations
            viz.add("test_task", "running", "Testing...")
            assert "test_task" in viz.statuses

            viz.update_status("test_task", "completed")
            assert viz.statuses["test_task"] == "completed"

            viz.remove("test_task")
            assert "test_task" not in viz.statuses

    @pytest.mark.asyncio
    @patch("pinjected.test_helper.rich_task_viz.Live")
    async def test_task_visualizer_cleanup(self, mock_live_class):
        """Test that cleanup happens even on error."""
        mock_live = MagicMock()
        mock_live_class.return_value = mock_live

        try:
            async with task_visualizer() as viz:
                viz.add("task", "running", "Working...")
                raise RuntimeError("Simulated error")
        except RuntimeError:
            pass

        # Live context should still be properly exited
        mock_live.__exit__.assert_called()


class TestEdgeCases:
    """Tests for edge cases and special scenarios."""

    @patch("pinjected.test_helper.rich_task_viz.Live")
    def test_empty_visualizer(self, mock_live_class):
        """Test visualizer with no tasks."""
        visualizer = RichTaskVisualizer()

        table = visualizer._generate_table()

        # Should still create a valid table
        assert isinstance(table, Table)
        assert table.title == "Current Tasks"
        assert len(table.columns) == 3
        # No rows should be added
        assert len(table.rows) == 0

    @patch("pinjected.test_helper.rich_task_viz.Live")
    def test_duplicate_task_names(self, mock_live_class):
        """Test handling of duplicate task names."""
        visualizer = RichTaskVisualizer()

        visualizer.add("task", "running", "First message")
        visualizer.add("task", "completed", "Second message")

        # Second add should overwrite the first
        assert visualizer.statuses["task"] == "completed"
        assert visualizer.messages["task"] == "Second message"

    @patch("pinjected.test_helper.rich_task_viz.Live")
    def test_unicode_support(self, mock_live_class):
        """Test Unicode characters in task names and messages."""
        visualizer = RichTaskVisualizer()

        visualizer.add("任务1", "运行中", "处理数据...")
        visualizer.add("tâche", "terminé", "Traitement terminé ✓")

        assert visualizer.statuses["任务1"] == "运行中"
        assert visualizer.messages["tâche"] == "Traitement terminé ✓"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
