import asyncio
from asyncio import Queue, Future
from typing import Union, AsyncIterator, Iterable
from pinjected.compatibility.task_group import TaskGroup

from pinjected import *

from tqdm import tqdm
from returns.future import future_safe


def ensure_agen(tasks):
    from inspect import isasyncgen
    if isinstance(tasks, list):
        async def agen():
            for t in tasks:
                yield t

        return agen()
    elif isasyncgen(tasks):
        return tasks
    elif hasattr(tasks, '__iter__'):
        async def agen():
            for t in tasks:
                yield t

        return agen()


@injected
async def a_map_progress__tqdm(
        async_f: callable,
        tasks: Union[AsyncIterator, list, Iterable],
        desc: str,
        pool_size: int = 16,
        total=None,
        wrap_result=False
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
        from loguru import logger
        nonlocal producer_status
        logger.info(f"starting producer with {tasks}")
        producer_status = "started"
        async for task in tasks:
            fut = Future()
            # logger.info(f"producing:{task}")
            producer_status = 'submitting'
            await queue.put((fut, task))
            producer_status = 'submitted'
            await result_queue.put(fut)
            producer_status = 'result future added'
            await asyncio.sleep(0)
        producer_status = 'done'
        for _ in range(pool_size):
            await queue.put((False, None))
        await result_queue.put(None)
        producer_status = 'finish signal submitted'
        return "producer done"

    consumer_status = dict()

    @future_safe
    async def safe_await(tgt: Future):
        return await tgt

    async def consumer(idx):
        from loguru import logger
        logger.info(f"starting consumer")
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
                    except Exception as e:
                        fut.set_exception(e)
                        continue
                    bar.update(1)
                    fut.set_result(res)
                case (False, None):
                    consumer_status[idx] = "done"
                    break
        return "consumer done"

    async with TaskGroup() as tg:
        producer_task = tg.create_task(producer())
        consumer_tasks = [tg.create_task(consumer(idx)) for idx in range(pool_size)]
        while True:
            done: Future = await result_queue.get()
            if done is None:
                break
            else:
                yield await done
