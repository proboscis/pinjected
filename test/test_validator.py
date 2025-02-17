import asyncio

import pytest

from pinjected import instances
from pinjected.di.util import validations
from pinjected.exceptions import DependencyValidationError
from pinjected.v2.keys import IBindKey
from pinjected.v2.async_resolver import AsyncResolver


def test_validation_works():
    from pinjected.pinjected_logging import logger
    def assert_int(key: IBindKey, value):
        logger.warning(f"asserting {key} {value}")
        assert isinstance(value, int), f"expected int got {value} for key {key}"

    d = instances(
        x=1,
        y="y"
    ) + validations(
        x=assert_int,
        y=assert_int
    )
    logger.debug(f"design:{d}")
    resolver = AsyncResolver(d)

    assert asyncio.run(resolver.provide('x')) == 1
    with pytest.raises(DependencyValidationError):
        assert asyncio.run(resolver.provide('y')) == 'y'
