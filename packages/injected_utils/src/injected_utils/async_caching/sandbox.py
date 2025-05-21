from injected_utils import async_cached_v2
from injected_utils.async_caching.async_cache import async_lzma_sqlite
from pinjected import Injected, IProxy, design, injected


@async_cached_v2(cache=async_lzma_sqlite("test.db"))
@injected
async def a_test_func(x: int, /, a: int, b: int) -> int:
    return a + b


test_call_a_test_func: IProxy = a_test_func(0, 1)
test_a_test_func: IProxy = Injected.tuple(
    a_test_func(0, 1),
    a_test_func(0, 1),
    a_test_func(0, 1),
)
from loguru import logger

__design__ = design(x=0, logger=logger)
