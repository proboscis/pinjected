import asyncio
import multiprocessing
from asyncio import Future
from dataclasses import dataclass
from typing import Callable, Any, Generic, TypeVar

"""
This module is to avoid using ProcessPoolExecutor, since it's buggy.
"""


def process_runner(func: Callable, args: tuple, result_queue: multiprocessing.Queue):
    try:
        result = func(*args)
        result_queue.put(("success", result))
    except Exception as e:
        result_queue.put(("error", str(e)))


T = TypeVar('T')


@dataclass
class FutureWithStd(Generic[T]):
    result: Future[T]
    stdout_queue: asyncio.Queue
    stderr_queue: asyncio.Queue

    async def _stream_from_queue(self, queue: asyncio.Queue):
        while True:
            kind, data = await queue.get()
            if kind == "end":
                break
            yield data

    async def stream_stdout(self):
        async for data in self._stream_from_queue(self.stdout_queue):
            yield data

    async def stream_stderr(self):
        async for data in self._stream_from_queue(self.stderr_queue):
            yield data


async def run_in_process(func: Callable, *args: Any) -> Any:
    result_queue = multiprocessing.Queue()
    process = multiprocessing.Process(
        target=process_runner,
        args=(func, args, result_queue),

    )

    # here, I want to capture the stdout and stderr of the process
    # and

    process.start()

    while True:
        if not process.is_alive():
            break
        if not result_queue.empty():
            break
        await asyncio.sleep(0.1)

    if not result_queue.empty():
        status, result = result_queue.get()
        if status == "error":
            raise RuntimeError(f"Function raised an exception: {result}")
        return result
    else:
        raise RuntimeError("Process ended without returning a result")
