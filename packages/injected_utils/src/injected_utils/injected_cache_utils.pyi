import asyncio
import inspect
from asyncio import Future
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ParamSpec, TypeVar, TypeAlias, overload

import pandas as pd
from sqlitedict import SqliteDict

from injected_utils.cached_function import (
    IKeyEncoder,
    IStringKeyProtocol,
    KeyEncoder,
)
from pinjected import Injected
from pinjected.providable import Providable

# AsyncResolver may not be available in all versions

P = ParamSpec("P")
T = TypeVar("T")
Hasher: TypeAlias = Callable[[P], Any]
HasherFactory: TypeAlias = Callable[[inspect.Signature], Hasher]

def ensure_injected(i: Providable) -> Injected: ...
def pickled_injected(cache_path: str | Path, injected: Injected) -> Any: ...
@dataclass
class AsyncRunTracker:
    logger: Any
    running_tasks: list[tuple[Future, Any, tuple, dict]]
    bound: Any

    def __post_init__(self) -> None: ...
    def log_status(self) -> None: ...
    def register(
        self, fut: Future, fn: Callable, *args: Any, **kwargs: Any
    ) -> None: ...

async def async_run(
    thread_pool: Any,
    AsyncRunTracker: AsyncRunTracker,
    /,
    fn: Callable[P, T],
    *args: P.args,
    **kwargs: P.kwargs,
) -> T: ...
async def run_in_new_thread(
    fn: Callable[P, T], /, *args: P.args, **kwargs: P.kwargs
) -> T: ...
def provide_cached(
    cache: dict, async_run: Callable, func: Callable, additional_key: Injected
) -> Callable[..., Any]: ...
def default_key_encoder(func: Callable) -> KeyEncoder: ...
def provide_cached_async(
    cache: dict,
    async_func: Callable,
    additonal_key: Any,
    en_async: Any,
    value_invalidator: Callable[[Any], bool] = ...,
    key_encoder_factory: Callable[[inspect.Signature], KeyEncoder] | None = None,
) -> Callable[..., Any]: ...
def to_async(
    async_run: Callable, /, func: Callable[P, T]
) -> Callable[P, asyncio.Coroutine[Any, Any, T]]: ...
def run_async(func: Injected[Callable]) -> Injected[Callable]: ...
def en_async_cached(
    cache: Injected[dict], *additional_keys: Injected
) -> Callable[[Injected[Callable]], Injected[Callable]]: ...
@dataclass
class HasherKeyEncoder(IKeyEncoder):
    hasher: Hasher

    def get_key(self, *args: Any, **kwargs: Any) -> str: ...

@overload
def async_cached(
    cache: Injected[dict],
    *additional_key: Injected,
    en_async: Any = None,
    value_invalidator: Callable[[Any], bool] | None = None,
    hasher_factory: Injected[HasherFactory] | None = None,
    key_hashers: None = None,
    replace_binding: bool = True,
) -> Callable[[Injected[Callable]], Injected[Callable]]: ...
@overload
def async_cached(
    cache: Injected[dict],
    *additional_key: Injected,
    en_async: Any = None,
    value_invalidator: Callable[[Any], bool] | None = None,
    hasher_factory: None = None,
    key_hashers: Injected[dict[str, Callable]] | None = None,
    replace_binding: bool = True,
) -> Callable[[Injected[Callable]], Injected[Callable]]: ...
@dataclass
class PicklableSqliteDict:
    src: SqliteDict

    def __reduce__(self) -> tuple[type[PicklableSqliteDict], tuple[str | Path]]: ...
    @classmethod
    def from_path(cls, path: str | Path) -> PicklableSqliteDict: ...
    def __getitem__(self, item: Any) -> Any: ...
    def __setitem__(self, key: Any, value: Any) -> None: ...
    def __contains__(self, item: Any) -> bool: ...
    def __delitem__(self, instance: Any) -> None: ...

@dataclass
class JsonBackedSqliteDict:
    src: SqliteDict

    def __reduce__(self) -> tuple[type[JsonBackedSqliteDict], tuple[str | Path]]: ...
    @classmethod
    def from_path(cls, path: str | Path) -> JsonBackedSqliteDict: ...
    def __getitem__(self, item: Any) -> Any: ...
    def __setitem__(self, key: Any, value: Any) -> None: ...
    def __contains__(self, item: Any) -> bool: ...
    def __delitem__(self, instance: Any) -> None: ...
    def values(self) -> list[Any]: ...
    def keys(self) -> list[Any]: ...

def sqlite_cache(cache_path: str | Path) -> PicklableSqliteDict: ...
def sqlite_dict(cache_path: str | Path) -> JsonBackedSqliteDict: ...
def sqlite_dict_with_backup(
    cache_path: str | Path, backup_frequency: pd.Timedelta
) -> JsonBackedSqliteDict: ...
@dataclass
class CustomKeyHasher:
    signature: inspect.Signature
    key_hasher: dict[str, Callable[[Any], Any]]
    type_hasher: dict[type, Callable[[Any], Any]]

    def __call__(self, *args: Any, **kwargs: Any) -> bytes: ...
    def calc_cache_key(self, *args: Any, **kwargs: Any) -> bytes: ...
    def encode_key(self, key: Any) -> Any: ...

default_custom_key_hasher_factory: Injected[CustomKeyHasher]

def custom_key_hasher_factory(
    key_hasher: dict[str, Callable] | None = None,
    type_hasher: dict[type, Callable] | None = None,
) -> Callable[[inspect.Signature], CustomKeyHasher]: ...
@dataclass
class HasherKeyProtocolAdapter(IStringKeyProtocol):
    hasher: Hasher

    def __call__(self, *args: Any, **kwargs: Any) -> Any: ...
    def get_cache_key(self, *args: Any, **kwargs: Any) -> Any: ...
    def encode_key(self, key: Any) -> Any: ...
    def decode_key(self, key: Any) -> Any: ...

def sync_cached(
    cache: Injected[dict],
    *deps: Injected,
    hasher_factory: Injected[HasherFactory] = ...,
) -> Callable[[Injected[Callable]], Injected[Callable]]: ...
def blocking_cached(
    cache: Injected[dict],
    *deps: Injected,
    protocol: Injected[IStringKeyProtocol] | None = None,
) -> Callable[[Injected[Callable]], Injected[Callable]]: ...
def parse_preference_assignments(res: dict) -> None: ...

__meta_design__: TypeAlias = Any
