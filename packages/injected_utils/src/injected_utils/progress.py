import asyncio
from asyncio import Future, Queue
from collections.abc import AsyncIterator, Iterable

from returns.future import future_safe
from tqdm import tqdm

from pinjected import *
from pinjected.compatibility.task_group import TaskGroup


def ensure_agen(tasks) -> AsyncIterator:  # noqa: C901
    """Convert various input types to async generators.

    Args:
        tasks: List, async generator, or iterable to convert

    Returns:
        AsyncIterator: An async generator yielding items from tasks

    Raises:
        TypeError: If tasks is a pandas DataFrame
    """
    from inspect import isasyncgen
    from typing import Any

    try:
        import pandas as pd

        if isinstance(tasks, pd.DataFrame):
            error_message = (
                "Iterating over a pandas DataFrame will iterate over column names rather than rows. "
                "Please convert to a list of rows using .iterrows(), .itertuples(), or .to_dict('records') instead."
            )
            raise TypeError(error_message)
    except ImportError:
        pass

    if isinstance(tasks, list):

        async def agen() -> AsyncIterator[Any]:
            for t in tasks:
                yield t

        return agen()
    if isasyncgen(tasks):
        return tasks
    if hasattr(tasks, "__iter__"):

        async def agen() -> AsyncIterator[Any]:
            for t in tasks:
                yield t

        return agen()

    return None  # Explicit return at the end of function


@injected
async def a_map_progress__tqdm(
    logger,
    /,
    async_f: callable,
    tasks: AsyncIterator | list | Iterable,
    desc: str,
    pool_size: int = 16,
    total=None,
    wrap_result=False,
):
    from returns.result import safe

    if total is None:
        total = safe(len)(tasks).value_or(total)
    bar = tqdm(total=total, desc=desc)
    queue = Queue()
    result_queue = Queue()
    tasks = ensure_agen(tasks)

    producer_status = "not started"

    async def producer():
        nonlocal producer_status
        # logger.info(f"starting producer with {tasks}")
        producer_status = "started"
        async for task in tasks:
            fut = Future()
            # logger.info(f"producing:{task}")
            producer_status = "submitting"
            await queue.put((fut, task))
            producer_status = "submitted"
            await result_queue.put(fut)
            producer_status = "result future added"
            await asyncio.sleep(0)
        producer_status = "done"
        for _ in range(pool_size):
            await queue.put((False, None))
        await result_queue.put(None)
        producer_status = "finish signal submitted"
        return "producer done"

    consumer_status = dict()

    @future_safe
    async def safe_await(tgt: Future):
        return await tgt

    async def consumer(idx):
        # logger.info(f"starting consumer")
        consumer_status[idx] = "started"
        while True:
            consumer_status[idx] = "waiting"
            match await queue.get():
                case (Future() as fut, task):
                    # logger.info(f"consuming {task}")
                    try:
                        consumer_status[idx] = "running"
                        if wrap_result:
                            res = await safe_await(async_f(task))
                        else:
                            res = await async_f(task)
                        fut.set_result(res)
                    except Exception as e:
                        fut.set_exception(e)
                    finally:
                        bar.update(1)
                case (False, None):
                    consumer_status[idx] = "done"
                    break
        return "consumer done"

    async with TaskGroup() as tg:
        logger.info("starting a_map_progress")
        producer_task = tg.create_task(producer())
        consumer_tasks = [tg.create_task(consumer(idx)) for idx in range(pool_size)]
        while True:
            done: Future = await result_queue.get()
            if done is None:
                break
            else:
                yield await done
        logger.success("a_map_progress done")
