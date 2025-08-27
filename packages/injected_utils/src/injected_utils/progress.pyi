from collections.abc import AsyncIterator, Callable, Iterable
from typing import Any, TypeVar, overload

from returns.future import FutureResult
from returns.result import Result

T = TypeVar("T")
U = TypeVar("U")

def ensure_agen(
    tasks: list[T] | AsyncIterator[T] | Iterable[T],
) -> AsyncIterator[T]: ...
@overload
async def a_map_progress__tqdm(
    async_f: Callable[[T], U],
    tasks: AsyncIterator[T] | list[T] | Iterable[T],
    desc: str,
    *,
    pool_size: int = 16,
    total: int | None = None,
    wrap_result: bool = False,
) -> AsyncIterator[U]: ...
@overload
async def a_map_progress__tqdm(
    async_f: Callable[[T], Result[U, Exception]],
    tasks: AsyncIterator[T] | list[T] | Iterable[T],
    desc: str,
    *,
    pool_size: int = 16,
    total: int | None = None,
    wrap_result: bool = True,
) -> AsyncIterator[Result[U, Exception]]: ...
@overload
async def a_map_progress__tqdm(
    async_f: Callable[[T], FutureResult[U, Exception]],
    tasks: AsyncIterator[T] | list[T] | Iterable[T],
    desc: str,
    *,
    pool_size: int = 16,
    total: int | None = None,
    wrap_result: bool = True,
) -> AsyncIterator[FutureResult[U, Exception]]: ...

__meta_design__: Any
