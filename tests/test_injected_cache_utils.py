import asyncio
from concurrent.futures import ThreadPoolExecutor

import loguru

from pinject_design import injected_function
from pinject_design.di.util import instances

@injected_function
async def async_run(thread_pool, logger, /, fn, *args, **kwargs):
    logger.info(f"async_run called with: {fn.__name__, args, kwargs}")
    fut = thread_pool.submit(fn, *args, **kwargs)
    return await asyncio.wrap_future(fut)


def test_async_run():
    d = instances(
        thread_pool=ThreadPoolExecutor(max_workers=1),
        logger=loguru.logger
    )
    g = d.to_graph()
    def func(x,y,z):
        print(x,y,z)
    asyncio.run(g[async_run](func,0,1,x=2))

