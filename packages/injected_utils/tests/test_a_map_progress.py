import asyncio

import loguru
from injected_utils.progress import a_map_progress__tqdm

from pinjected import design
from pinjected.compatibility.task_group import CompatibleExceptionGroup
from pinjected.test import injected_pytest


@injected_pytest
async def test_a_map_progress__tqdm(a_map_progress__tqdm):
    async def task(item):
        return item

    items = list(range(10))
    agen = a_map_progress__tqdm(
        task,
        items,
        total=len(items),
        desc="Testing a_map_progress",
    )
    res = [item async for item in agen]
    assert res == items


class DummyException(Exception):
    pass


@injected_pytest
async def test_a_map_progress__tqdm_raise_exception(
    a_map_progress__tqdm,
):
    async def task(item):
        await asyncio.sleep(1)
        if item == 5:
            raise DummyException("Test exception")
        return item

    items = list(range(10))
    try:
        agen = a_map_progress__tqdm(
            task,
            items,
            total=len(items),
            desc="Testing a_map_progress",
        )
        res = [item async for item in agen]
        raise AssertionError("Expected exception not raised")
    except Exception as e:
        if isinstance(e, CompatibleExceptionGroup):
            if any(isinstance(ex, DummyException) for ex in e.exceptions):
                pass
            else:
                raise AssertionError(f"Unexpected exception raised: {e}")
        elif isinstance(e, DummyException):
            pass
        else:
            raise AssertionError(f"Unexpected exception raised: {e}")


def test_exception_group():
    def func():
        raise DummyException("Test exception")

    try:
        func()
    except Exception as e:
        if isinstance(e, CompatibleExceptionGroup):
            if any(isinstance(ex, DummyException) for ex in e.exceptions):
                # so we can catch the exception group, even the src exception is just single.
                pass
            else:
                raise AssertionError(f"Unexpected exception raised: {e}")
        elif isinstance(e, DummyException):
            pass
        else:
            raise AssertionError(f"Unexpected exception raised: {e}")


__design__ = design(a_map_progress__tqdm=a_map_progress__tqdm, logger=loguru.logger)
