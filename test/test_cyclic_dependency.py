import asyncio

import pytest

from pinjected import design, injected, Injected
from pinjected.exceptions import DependencyResolutionError
from pinjected.pinjected_logging import logger

from pinjected.v2.async_resolver import AsyncResolver


def test_validation():
    # 重複キーを避けるため、別々のdesignを作成して結合
    d = design(
        x=0
    )
    d = d + design(
        y=Injected.bind(lambda x: x)
    )
    d = d + design(
        x=Injected.bind(lambda y: y)
    )
    with pytest.raises(DependencyResolutionError) as e:
        asyncio.run(AsyncResolver(d)['y'])
    logger.info(f"successfully detected dep error as :{e}")
    with pytest.raises(DependencyResolutionError) as e:
        asyncio.run(AsyncResolver(d)['z'])
    logger.info(f"successfully detected dep error as :{e}")
    with pytest.raises(DependencyResolutionError) as e:
        asyncio.run(AsyncResolver(d)[injected('z') + injected('z')])
    logger.info(f"successfully detected dep error as :{e}")
    d2 = design(
        x=0,
        y=Injected.bind(lambda x: 1)
    )

    assert asyncio.run(AsyncResolver(d2)[injected('y') + injected('y')]) == 2
