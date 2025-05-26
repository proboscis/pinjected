from collections.abc import Awaitable, Callable
from typing import Any, TypeAlias, overload

from injected_utils.async_caching.async_cached_function import (
    AsyncCacheProtocol,
    InvalidateValue,
    IsErrorToRetry,
    Key,
    P,
    ParamToKey,
    U,
)
from pinjected.di.injected import PartialInjectedFunction

Cache: TypeAlias = AsyncCacheProtocol[Key, U]
Func: TypeAlias = Callable[[P], Awaitable[U]]

Serializer: TypeAlias = Callable[[Any], Awaitable[bytes]]
Deserializer: TypeAlias = Callable[[bytes], Awaitable[Any]]

def async_injected_decorator(
    decorator: PartialInjectedFunction,
) -> Callable[..., Callable[[Func], Func]]: ...
@overload
def async_cached_v2(
    cache: Cache,
    *,
    a_param_to_key: ParamToKey = None,
    a_is_error_to_retry: IsErrorToRetry = None,
    a_invalidate_value: InvalidateValue = None,
    a_serializer: Serializer = None,
    a_deserializer: Deserializer = None,
) -> Callable[[Func], Callable[P, Awaitable[U]]]: ...
async def injected_utils_default_param_to_key(
    *args: tuple, **kwargs: dict
) -> bytes: ...
async def injected_utils_default_is_error_to_retry(e: Exception) -> str: ...
async def injected_utils_default_invalidate_value(inputs: tuple, value: U) -> str: ...
async def __mock_cache() -> AsyncCacheProtocol[bytes, Any]: ...
async def injected_utils_default_serializer(data: Any) -> bytes: ...
async def injected_utils_default_deserializer(data: bytes) -> Any: ...

__meta_design__: TypeAlias = Any
