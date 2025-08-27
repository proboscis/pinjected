"""Simple tests for test_helper/rich_task_viz.py module."""

import pytest
from unittest.mock import patch, Mock
from dataclasses import is_dataclass, fields

from pinjected.test_helper.rich_task_viz import RichTaskVisualizer, task_visualizer


class TestRichTaskVisualizer:
    """Test the RichTaskVisualizer class."""

    def test_rich_task_visualizer_is_dataclass(self):
        """Test that RichTaskVisualizer is a dataclass."""
        assert is_dataclass(RichTaskVisualizer)

    def test_rich_task_visualizer_fields(self):
        """Test RichTaskVisualizer dataclass fields."""
        field_names = {f.name for f in fields(RichTaskVisualizer)}
        assert "statuses" in field_names
        assert "messages" in field_names
        assert "console" in field_names
        assert "live" in field_names

    def test_rich_task_visualizer_init(self):
        """Test RichTaskVisualizer initialization."""
        # Create visualizer with explicit console to avoid mocking issues
        from rich.console import Console

        console = Console()
        viz = RichTaskVisualizer(console=console)

        # Check defaults
        assert viz.statuses == {}
        assert viz.messages == {}
        assert viz.console is console
        assert hasattr(viz, "live")
        assert viz.live is not None

        # Check Live attributes
        assert viz.live.console is console
        assert viz.live.refresh_per_second == 8

    @patch("pinjected.test_helper.rich_task_viz.Live")
    def test_add_task(self, mock_live_class):
        """Test adding a task."""
        mock_live = Mock()
        mock_live_class.return_value = mock_live

        viz = RichTaskVisualizer()
        viz.add("task1", "running", "Processing data")

        assert viz.statuses["task1"] == "running"
        assert viz.messages["task1"] == "Processing data"

        # Check update was called
        mock_live.update.assert_called()

    @patch("pinjected.test_helper.rich_task_viz.Live")
    def test_update_status(self, mock_live_class):
        """Test updating task status."""
        mock_live = Mock()
        mock_live_class.return_value = mock_live

        viz = RichTaskVisualizer()
        viz.statuses["task1"] = "running"
        viz.messages["task1"] = "Processing"

        viz.update_status("task1", "completed")

        assert viz.statuses["task1"] == "completed"
        mock_live.update.assert_called()

    @patch("pinjected.test_helper.rich_task_viz.Live")
    def test_remove_task(self, mock_live_class):
        """Test removing a task."""
        mock_live = Mock()
        mock_live_class.return_value = mock_live

        viz = RichTaskVisualizer()
        viz.statuses["task1"] = "running"
        viz.messages["task1"] = "Processing"

        viz.remove("task1")

        assert "task1" not in viz.statuses
        assert "task1" not in viz.messages
        mock_live.update.assert_called()

    @patch("pinjected.test_helper.rich_task_viz.Live")
    def test_remove_nonexistent_task(self, mock_live_class):
        """Test removing a task that doesn't exist."""
        mock_live = Mock()
        mock_live_class.return_value = mock_live

        viz = RichTaskVisualizer()

        # Should not raise error
        viz.remove("nonexistent")
        mock_live.update.assert_called()

    @patch("pinjected.test_helper.rich_task_viz.Live")
    def test_update_message(self, mock_live_class):
        """Test updating task message."""
        mock_live = Mock()
        mock_live_class.return_value = mock_live

        viz = RichTaskVisualizer()
        viz.statuses["task1"] = "running"
        viz.messages["task1"] = "Starting"

        viz.update_message("task1", "50% complete")

        assert viz.messages["task1"] == "50% complete"
        mock_live.update.assert_called()

    @patch("pinjected.test_helper.rich_task_viz.Live")
    def test_update_message_nonexistent(self, mock_live_class):
        """Test updating message for nonexistent task."""
        mock_live = Mock()
        mock_live_class.return_value = mock_live

        viz = RichTaskVisualizer()

        # Should not update if task doesn't exist
        viz.update_message("nonexistent", "message")

        assert "nonexistent" not in viz.messages
        mock_live.update.assert_called()

    @patch("pinjected.test_helper.rich_task_viz.Table")
    def test_generate_table(self, mock_table_class):
        """Test table generation."""
        mock_table = Mock()
        mock_table_class.return_value = mock_table

        # Create a visualizer - this will call _generate_table once in __post_init__
        viz = RichTaskVisualizer()
        viz.statuses = {"task1": "running", "task2": "completed"}
        viz.messages = {"task1": "Processing", "task2": "Done"}

        # Reset the mock to clear calls from __post_init__
        mock_table_class.reset_mock()
        mock_table.reset_mock()

        # Now test _generate_table directly
        result = viz._generate_table()

        # Check table was created with title
        mock_table_class.assert_called_once_with(title="Current Tasks")

        # Check columns were added
        assert mock_table.add_column.call_count == 3
        mock_table.add_column.assert_any_call("Task", style="cyan")
        mock_table.add_column.assert_any_call("Status", style="magenta")
        mock_table.add_column.assert_any_call("Message", style="green")

        # Check rows were added
        assert mock_table.add_row.call_count == 2

        # Check the result is the mock table
        assert result is mock_table


class TestTaskVisualizer:
    """Test the task_visualizer async context manager."""

    @pytest.mark.asyncio
    async def test_task_visualizer_context_manager(self):
        """Test task_visualizer as async context manager."""
        with patch(
            "pinjected.test_helper.rich_task_viz.RichTaskVisualizer"
        ) as mock_viz_class:
            mock_viz = Mock()
            mock_live = Mock()
            mock_viz.live = mock_live
            mock_viz_class.return_value = mock_viz

            # Setup mock Live to support context manager
            mock_live.__enter__ = Mock(return_value=mock_live)
            mock_live.__exit__ = Mock(return_value=None)

            # Use as context manager
            async with task_visualizer() as viz:
                assert viz == mock_viz
                mock_live.__enter__.assert_called_once()

            # Check cleanup
            mock_live.__exit__.assert_called_once()

    @pytest.mark.asyncio
    async def test_task_visualizer_exception_handling(self):
        """Test task_visualizer handles exceptions properly."""
        with patch(
            "pinjected.test_helper.rich_task_viz.RichTaskVisualizer"
        ) as mock_viz_class:
            mock_viz = Mock()
            mock_live = Mock()
            mock_viz.live = mock_live
            mock_viz_class.return_value = mock_viz

            # Setup mock Live to support context manager
            mock_live.__enter__ = Mock(return_value=mock_live)
            mock_live.__exit__ = Mock(return_value=None)

            # Test exception is propagated
            with pytest.raises(ValueError):
                async with task_visualizer():
                    raise ValueError("Test error")

            # Live context should still be exited
            mock_live.__exit__.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
