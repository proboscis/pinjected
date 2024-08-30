import asyncio
import inspect

import pytest
from frozendict import frozendict

from pinjected import *
from pinjected import Injected
from pinjected.di.partially_injected import Partial
from loguru import logger

from pinjected.v2.resolver import AsyncResolver


def target_function(d1, d2, d3, /, a, b, *args, named=4, **kwargs):
    return frozendict(
        d1=d1,
        d2=d2,
        d3=d3,
        a=a,
        b=b,
        args=args,
        named=named,
        kwargs=kwargs
    )


wrapped = Partial(
    target_function,
    injection_targets=dict(
        d1=Injected.pure(1),
        d2=Injected.pure(2),
        d3=Injected.pure(3)
    )
)
target_result = target_function(1, 2, 3, 'a', 'b', 'args1', 'args2', named=5, kw1='kw1', kw2='kw2')
target_without_args = target_function(1, 2, 3, 'a', 'b', named=5, kw1='kw1', kw2='kw2')


def test_partial():
    logger.info(wrapped.func_sig)
    logger.info(wrapped.get_modified_signature())
    bound = wrapped.modified_sig.bind(
        'a', 'b', 'args1', 'args2', named=5, kw1='kw1', kw2='kw2'
    )
    logger.info(f'bound: {bound.arguments}')
    logger.info(f'bound.args: {bound.args}')
    logger.info(f'bound.kwargs: {bound.kwargs}')


def test_new_args_kwargs():
    args, kwargs = wrapped.final_args_kwargs(
        dict(
            d1=1,
            d2=2,
            d3=3
        ),
        'a', 'b', 'args1', 'args2', named=5, kw1='kw1', kw2='kw2'
    )
    logger.info(f'args: {args}')
    logger.info(f'kwargs: {kwargs}')
    logger.info(f"expected: {target_result}")
    result = wrapped.src_function(*args, **kwargs)
    assert result == target_result


def test_partial_injected():
    provider = wrapped.get_provider()
    logger.info(provider)
    provider_sig = inspect.signature(provider)
    logger.info(provider_sig)
    func = asyncio.run(provider())
    logger.info(func("a", "b", "args1", "args2", named=5, kw1='kw1', kw2='kw2'))

@pytest.mark.asyncio
async def test_with_design():
    wrapped = Partial(
        target_function,
        injection_targets=dict(
            d1=Injected.by_name('d1'),
            d2=Injected.by_name('d2'),
            d3=Injected.by_name('d3')
        )
    )
    d = instances(
        d1=1,
        d2=2,
        d3=3
    )
    r = AsyncResolver(d)
    data = await r[wrapped('a', 'b', 'args1', 'args2', named=5, kw1='kw1', kw2='kw2')]
    assert data == target_result


def test_with_injected_decorator():
    wrapped = injected(target_function)
    d = instances(
        d1=1,
        d2=2,
        d3=3
    )
    assert d.provide(wrapped('a', 'b', 'args1', 'args2', named=5, kw1='kw1', kw2='kw2')) == target_result

if __name__ == '__main__':
    test_with_injected_decorator()