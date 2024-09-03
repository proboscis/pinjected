import asyncio
import multiprocessing
from typing import Callable, Any

"""
This module is to avoid using ProcessPoolExecutor, since it's buggy.
"""

def process_runner(func: Callable, args: tuple, result_queue: multiprocessing.Queue):
    try:
        result = func(*args)
        result_queue.put(("success", result))
    except Exception as e:
        result_queue.put(("error", str(e)))

async def run_in_process(func: Callable, *args: Any) -> Any:
    result_queue = multiprocessing.Queue()
    process = multiprocessing.Process(target=process_runner, args=(func, args, result_queue))

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