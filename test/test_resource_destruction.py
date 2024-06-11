import asyncio
import time
from concurrent.futures import ThreadPoolExecutor, Future
from threading import Thread

import pytest

from pinjected import *
from pinjected.compatibility.task_group import TaskGroup

design = instances(
    x='x',
    y='y'
) + destructors(
    x=lambda: lambda x: print(f"destroying {x}")
)


def test_destruction_runs():
    res = design.to_resolver()
    assert asyncio.run(res['x']) == 'x'
    assert asyncio.run(res.destruct()) == [None]


def test_infinite_task():
    fut = Future()

    def loop_task():
        for i in range(10):
            print(f"looping")
            time.sleep(0.5)
        fut.set_exception(Exception('Exception!'))

    async def main():
        async with TaskGroup() as tg:
            async def task_waiter():
                print(f"raising exception")
                raise RuntimeError('Exception!')

            # you must await this task to catch the exception
            async def task2():
                for i in range(3):
                    print(f"main {i}")
                    await asyncio.sleep(1)

            Thread(target=loop_task, daemon=True).start()
            a_fut = asyncio.wrap_future(fut, loop=asyncio.get_event_loop())

            async def loop_waiter():
                return await a_fut

            tg.create_task(loop_waiter())
            tg.create_task(task_waiter())
            tg.create_task(task2())
            # aha, long running thread won't get killed. but other tasks gets cancelled
            # I mean, daemon threads can be killed by the main thread. so use it! :)

    with pytest.raises(ExceptionGroup):
        asyncio.run(main())
