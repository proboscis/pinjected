from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from pinjected import IProxy

T = TypeVar("T")
U = TypeVar("U")

def _async_batch_cached(
    cache: dict[str, U],
    hasher: Callable[[T], str] | None = None,
) -> Callable[
    [Callable[[tuple[T, ...]], Awaitable[list[U]]]],
    Callable[[tuple[T, ...]], Awaitable[list[U]]],
]: ...
def async_batch_cached(
    cache: IProxy[dict[str, U]],
    hasher: Callable[[T], str] | None = None,
) -> Callable[[IProxy], IProxy]: ...
async def _test_function_batch_cached(*items: Any) -> tuple[Any, ...]: ...

run_test_function_batch_cached: IProxy

__meta_design__: Any
