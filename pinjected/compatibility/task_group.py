import asyncio
import multiprocessing


class ExceptionGroup(Exception):
    def __init__(self, exceptions):
        self.exceptions = exceptions


try:
    from asyncio import TaskGroup
    # Python 3.11+ has TaskGroup, so we don't need our implementation
except ImportError:
    from pinjected.pinjected_logging import logger

    current_process = multiprocessing.current_process()
    if "SpawnProcess" not in current_process.name:
        logger.warning(
            "Using compatibility.task_group.TaskGroup since TaskGroup from python 3.11 is not available."
        )

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
            try:
                await asyncio.gather(*self.tasks, return_exceptions=False)
            except Exception as e:
                raise ExceptionGroup([e]) from e


CompatibleExceptionGroup = ExceptionGroup
