import asyncio
import multiprocessing

try:
    from asyncio import TaskGroup
except ImportError:
    from loguru import logger
    current_process = multiprocessing.current_process()
    if "SpawnProcess" not in current_process.name:
        logger.warning(f"Using compatibility.task_group.TaskGroup since TaskGroup from python 3.11 is not available.")
    class TaskGroup:
        def __init__(self):
            self.tasks = []

        def create_task(self, coro):
            task = asyncio.create_task(coro)
            self.tasks.append(task)
            return task

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            results = await asyncio.gather(*self.tasks,return_exceptions=False)
