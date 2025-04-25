import loguru

from injected_utils import async_cached
from pinjected import injected, Injected, IProxy, design
from pinjected.test import injected_pytest


@async_cached(cache=Injected.pure(dict()))
@injected
async def impl_function():
    raise NotImplementedError()

@injected_pytest()
async def test_impl_function(impl_function):
    await impl_function()


run_impl:IProxy = impl_function()
__design__ = design(
    logger=loguru.logger
)