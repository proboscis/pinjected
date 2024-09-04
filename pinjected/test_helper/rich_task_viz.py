from asyncio import Future
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Dict, AsyncIterator

from rich.console import Console
from rich.live import Live
from rich.table import Table


@dataclass
class RichTaskVisualizer:
    """
    Visualize the tasks in progress in async. No progress bar.
    Shows one line message per task.
    """
    tasks: Dict[str, str] = field(default_factory=dict)
    console: Console = field(default_factory=Console)
    live: Live = field(init=False)

    def __post_init__(self):
        self.live = Live(self._generate_table(), console=self.console, refresh_per_second=4)

    def add(self, name: str, message: str):
        """Add a new task with the given message."""
        self.tasks[name] = message
        self.update()

    def remove(self, name: str):
        """Remove a task."""
        if name in self.tasks:
            del self.tasks[name]
            self.update()

    def update_message(self, name: str, message: str):
        """Update the message for a specific task."""
        if name in self.tasks:
            self.tasks[name] = message
            self.update()

    def _generate_table(self) -> Table:
        """Generate a table showing current tasks."""
        table = Table(title="Current Tasks")
        table.add_column("Task Name", style="cyan")
        table.add_column("Status", style="magenta")

        for name, message in self.tasks.items():
            table.add_row(name, message)

        return table

    def update(self):
        """Update the live display."""
        self.live.update(self._generate_table())


@asynccontextmanager
async def task_visualizer() -> AsyncIterator[RichTaskVisualizer]:
    """
    AsyncContextManager for RichTaskVisualizer.
    Usage:
    async with task_visualizer() as visualizer:
        # Use visualizer here
    """
    visualizer = RichTaskVisualizer()
    try:
        with visualizer.live:
            yield visualizer
    finally:
        # Cleanup code if needed
        pass