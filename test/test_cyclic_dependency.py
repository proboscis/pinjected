import asyncio

import pytest

from pinjected import instances, providers, injected
from pinjected.exceptions import DependencyResolutionError
from loguru import logger


def test_validation():
    d = instances(
        x = 0
    ) + providers(
        y = lambda x: x,
        x = lambda y: y
    )
    with pytest.raises(DependencyResolutionError) as e:
        asyncio.run(d.to_resolver()['y'])
    logger.info(f"successfully detected dep error as :{e}")
    with pytest.raises(DependencyResolutionError) as e:
        asyncio.run(d.to_resolver()['z'])
    logger.info(f"successfully detected dep error as :{e}")
    with pytest.raises(DependencyResolutionError) as e:
        asyncio.run(d.to_resolver()[injected('z') + injected('z')])
    logger.info(f"successfully detected dep error as :{e}")
    d2 =instances(
        x = 0
    ) + providers(
        y = lambda x:1
    )
    assert asyncio.run(d2.to_resolver()[injected('y') + injected('y')]) == 2
