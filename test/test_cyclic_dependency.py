import asyncio
import sys

import pytest

from pinjected import Injected, design, injected
from pinjected.exceptions import DependencyResolutionError
from pinjected.pinjected_logging import logger
from pinjected.v2.async_resolver import AsyncResolver

# Use the appropriate ExceptionGroup based on Python version
if sys.version_info >= (3, 11):
    # Python 3.11+ has native ExceptionGroup
    ExceptionGroup = BaseExceptionGroup  # noqa: F821
else:
    # Python < 3.11 uses our compatibility ExceptionGroup
    from pinjected.compatibility.task_group import ExceptionGroup


def test_validation():
    # 重複キーを避けるため、別々のdesignを作成して結合
    d = design(x=0)
    d = d + design(y=Injected.bind(lambda x: x))
    d = d + design(x=Injected.bind(lambda y: y))
    with pytest.raises(ExceptionGroup) as e:
        asyncio.run(AsyncResolver(d)["y"])
    # Check that the ExceptionGroup contains the expected DependencyResolutionError
    assert len(e.value.exceptions) == 1
    assert isinstance(e.value.exceptions[0], DependencyResolutionError)
    logger.info(f"successfully detected dep error as :{e}")

    with pytest.raises(ExceptionGroup) as e:
        asyncio.run(AsyncResolver(d)["z"])
    # Check that the ExceptionGroup contains the expected DependencyResolutionError
    assert len(e.value.exceptions) == 1
    assert isinstance(e.value.exceptions[0], DependencyResolutionError)
    logger.info(f"successfully detected dep error as :{e}")

    with pytest.raises(ExceptionGroup) as e:
        asyncio.run(AsyncResolver(d)[injected("z") + injected("z")])
    # Check that the ExceptionGroup contains the expected DependencyResolutionError
    assert len(e.value.exceptions) == 1
    assert isinstance(e.value.exceptions[0], DependencyResolutionError)
    logger.info(f"successfully detected dep error as :{e}")
    d2 = design(x=0, y=Injected.bind(lambda x: 1))

    assert asyncio.run(AsyncResolver(d2)[injected("y") + injected("y")]) == 2
