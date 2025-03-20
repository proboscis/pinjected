import asyncio

import pytest
from returns.future import future_safe
from returns.maybe import Some

from pinjected import design
from pinjected import injected
from pinjected.di.design_spec.impl import DesignSpecImpl, BindSpecImpl, SimpleBindSpec
from pinjected.exceptions import DependencyValidationError, DependencyResolutionError
from pinjected.pinjected_logging import logger
from pinjected.v2.async_resolver import AsyncResolver
from pinjected.v2.keys import IBindKey, StrBindKey


@future_safe
async def assert_int(key: IBindKey, value):
    logger.warning(f"asserting {key} {value}")
    assert isinstance(value, int), f"expected int got {value} for key {key}"
    return "success"


@future_safe
async def doc_for_z(key):
    return "z is not provided"


@future_safe
async def doc_for_key(key):
    return f"{key} is not provided. Please provide it."


@injected
async def provide_value(a, b, x, /):
    return x


def test_validation_works():
    d = design(
        x=1,
        y="y",
        X=provide_value()
    )
    spec = DesignSpecImpl(
        specs={
            StrBindKey('x'): BindSpecImpl(
                validator=Some(assert_int)
            ),
            StrBindKey('y'): BindSpecImpl(
                validator=Some(assert_int),
            ),
            StrBindKey('z'): SimpleBindSpec(
                documentation='z is not provided',
            ),
            StrBindKey('a'): SimpleBindSpec(
                documentation="a is not provided. Please provide it"
            ),
        }
    )
    logger.debug(f"design:{d}")
    # test fails due IMPLICIT_BINDINGS. so we disable it like this.
    resolver = AsyncResolver(d, spec=spec,use_implicit_bindings=False)

    assert asyncio.run(resolver.provide('x')) == 1
    with pytest.raises(DependencyValidationError):
        # this fails because y is "y" not an int
        assert asyncio.run(resolver.provide('y')) == 'y'
    with pytest.raises(DependencyResolutionError) as e:
        # THIS is not raising anything?
        logger.info(f"checking for provision errors")
        errors = asyncio.run(resolver.a_find_provision_errors('z'))
        logger.debug(f"checking find_provision_errors of 'z' got errors:{errors}")
        asyncio.run(resolver.a_check_resolution('z'))
        logger.error('check_resolution did not raise')
    with pytest.raises(DependencyResolutionError) as e:
        # This raises keyerror rather than DependencyResolutionError.
        data = asyncio.run(resolver.provide('z'))
        logger.error(f"got data:{data}")
    logger.debug(f"got error:{e}")
    logger.debug(f"got error:{e.value}")
    assert 'z is not provided' in str(e.value), f"expected 'z is not provided' in {e.value}"
    with pytest.raises(DependencyResolutionError) as e:
        assert asyncio.run(resolver.provide('X'))
    logger.debug(f"got error:{e}")
    logger.debug(f"got error:{e.value}")
    assert 'Please provide it' in str(e.value), f"expected 'Please provide it' in {e.value}"
