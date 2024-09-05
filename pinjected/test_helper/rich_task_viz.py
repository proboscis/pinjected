from asyncio import Future
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Dict, AsyncIterator

from rich.console import Console, ConsoleRenderable
from rich.live import Live
from rich.table import Table


@dataclass
class RichTaskVisualizer:
    """
    Visualize the tasks in progress in async. No progress bar.
    Shows one line message per task.
    """
    statuses: Dict[str, ConsoleRenderable | str] = field(default_factory=dict)
    messages: Dict[str, ConsoleRenderable | str] = field(default_factory=dict)
    console: Console = field(default_factory=Console)
    live: Live = field(init=False)

    def __post_init__(self):
        self.live = Live(self._generate_table(), console=self.console, refresh_per_second=8)

    def add(self, name: str, status, message: str | ConsoleRenderable):
        """Add a new task with the given message."""
        self.statuses[name] = status
        self.messages[name] = message
        self.update()

    def update_status(self, name: str, status: str):
        self.statuses[name] = status
        self.update()

    def remove(self, name: str | ConsoleRenderable):
        """Remove a task."""
        if name in self.statuses:
            del self.statuses[name]
        if name in self.messages:
            del self.messages[name]
        self.update()


    def update_message(self, name: str, message: str | ConsoleRenderable):
        """Update the message for a specific task."""
        if name in self.statuses:
            self.messages[name] = message
        self.update()

    def _generate_table(self) -> Table:
        """Generate a table showing current tasks."""
        table = Table(title="Current Tasks")
        table.add_column("Task", style="cyan")
        table.add_column("Status", style="magenta")
        table.add_column("Message", style="green")

        for name in self.statuses.keys():
            status = self.statuses[name]
            message = self.messages[name]
            table.add_row(name, status, message)

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
