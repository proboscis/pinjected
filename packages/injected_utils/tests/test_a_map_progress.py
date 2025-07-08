import asyncio

import loguru
import pytest
from injected_utils.progress import a_map_progress__tqdm, ensure_agen

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
        [item async for item in agen]
        raise AssertionError("Expected exception not raised")
    except Exception as e:
        # Handle both native Python 3.11+ ExceptionGroup and compatibility ExceptionGroup
        if hasattr(e, "exceptions"):  # ExceptionGroup-like object
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


def test_ensure_agen_with_dataframe():
    """Test that ensure_agen raises TypeError when given a pandas DataFrame."""
    import pandas as pd

    test_dataframe = pd.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]})

    with pytest.raises(
        TypeError,
        match="Iterating over a pandas DataFrame will iterate over column names rather than rows",
    ):
        ensure_agen(test_dataframe)


__design__ = design(a_map_progress__tqdm=a_map_progress__tqdm, logger=loguru.logger)
