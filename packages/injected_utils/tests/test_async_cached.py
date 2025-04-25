import loguru
import pytest

from injected_utils import async_cached
from injected_utils.cached_function import CacheNewValueValidationFailure
from pinjected import injected, Injected, IProxy, design
from pinjected.test import injected_pytest

@injected
async def a_failure_validation(item):
    return f"failed to validate {item}"

@injected
async def a_errorneous_validator(item):
    raise RuntimeError(f"failed to validate {item}")

@injected
async def a_invalid_validator():
    raise RuntimeError("failed to validate")

@async_cached(
    cache=Injected.pure(dict()),
    value_invalidator=a_failure_validation,
)
@injected
async def impl_function():
    return 42

@async_cached(
    cache=Injected.pure(dict()),
    value_invalidator=a_errorneous_validator,
)
@injected
async def impl_function_2():
    return 42

@async_cached(
    cache=Injected.pure(dict()),
    value_invalidator=a_invalid_validator,
)
@injected
async def impl_function_3():
    return 42

@injected_pytest()
async def test_impl_function(impl_function):
    with pytest.raises(CacheNewValueValidationFailure):
        await impl_function()

@injected_pytest()
async def test_impl_function_2(impl_function_2):
    with pytest.raises(RuntimeError):
        await impl_function_2()

@injected_pytest()
async def test_impl_function_3(impl_function_3):
    with pytest.raises(TypeError):
        await impl_function_3()

@injected
async def a_valid_validator(item):
    return

@async_cached(
    cache=Injected.pure(dict()),
    value_invalidator=a_valid_validator,
)
@injected
async def impl_function_4():
    return 42

@injected_pytest()
async def test_impl_function_4(logger,impl_function_4):
    assert (x:=await impl_function_4()) == 42, f'Expected 42 for first, but got {x}'
    logger.info(f"First call result: {x}")
    assert (x:=await impl_function_4()) == 42, f'Expected 42 for second, but got {x}'
    logger.info(f"Second call result: {x}")
    assert (x:=await impl_function_4()) == 42, f'Expected 42 for third, but got {x}'
    logger.info(f"Third call result: {x}")


run_impl:IProxy = impl_function()
__design__ = design(
    logger=loguru.logger
)