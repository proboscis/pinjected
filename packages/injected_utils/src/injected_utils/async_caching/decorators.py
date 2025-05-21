import hashlib
import inspect
from collections.abc import Awaitable, Callable
from typing import Any

import jsonpickle
from returns.maybe import Some

from injected_utils.async_caching.async_cached_function import (
    AsyncCachedFunctionV2,
    AsyncCacheProtocol,
    InvalidateValue,
    IsErrorToRetry,
    Key,
    P,
    ParamToKey,
    ThreadPooledDictAsyncCache,
    U,
    ValueMappedAsyncCache,
)
from pinjected import Injected, design, injected
from pinjected.decoration import update_if_registered
from pinjected.di.injected import PartialInjectedFunction
from pinjected.di.metadata.bind_metadata import BindMetadata
from pinjected.di.util import get_code_location

Cache = AsyncCacheProtocol[Key, U]
Func = Callable[[P], Awaitable[U]]

Serializer = Callable[[Any], Awaitable[bytes]]
Deserializer = Callable[[bytes], Awaitable[Any]]


def async_injected_decorator(decorator: PartialInjectedFunction):
    """
    Use this to implement a decorator for @injected functions.
    :param decorator:
    :return:
    """
    parent_frame = inspect.currentframe().f_back

    def decorater_impl(*args, **kwargs):
        deco_proxy = decorator(*args, **kwargs)

        def impl(func: Func):
            proxy = deco_proxy(func)
            proxy.__is_async_function__ = True
            updated = Injected.ensure_injected(proxy)
            updated.__is_async_function__ = True
            updated = update_if_registered(
                func=func,
                updated=updated,
                meta=Some(
                    BindMetadata(code_location=Some(get_code_location(parent_frame)))
                ),
            )
            return updated

        return impl

    return decorater_impl


@async_injected_decorator
@injected
def async_cached_v2(
    injected_utils_default_param_to_key: ParamToKey,
    injected_utils_default_is_error_to_retry: IsErrorToRetry,
    injected_utils_default_invalidate_value: InvalidateValue,
    injected_utils_default_serializer: Serializer,
    injected_utils_default_deserializer: Deserializer,
    /,
    cache: Cache,
    a_param_to_key: ParamToKey = None,
    a_is_error_to_retry: IsErrorToRetry = None,
    a_invalidate_value: InvalidateValue = None,
    a_serializer: Serializer = None,
    a_deserializer: Deserializer = None,
):
    def impl(a_func: Func):
        mapped = ValueMappedAsyncCache(
            src=cache,
            a_mapper=a_serializer or injected_utils_default_serializer,
            a_inverse_mapper=a_deserializer or injected_utils_default_deserializer,
        )
        return AsyncCachedFunctionV2(
            a_func=a_func,
            a_param_to_key=a_param_to_key or injected_utils_default_param_to_key,
            cache=mapped,
            a_is_error_to_retry=a_is_error_to_retry
            or injected_utils_default_is_error_to_retry,
            a_invalidate_value=a_invalidate_value
            or injected_utils_default_invalidate_value,
        )

    return impl


@injected
async def injected_utils_default_param_to_key(args: tuple, kwargs: dict) -> bytes:
    data = jsonpickle.dumps((args, kwargs))
    hash = hashlib.md5(data.encode()).hexdigest()
    return hash.encode()


@injected
async def injected_utils_default_is_error_to_retry(e: Exception) -> str:
    return ""


@injected
async def injected_utils_default_invalidate_value(inputs: tuple, value: U) -> str:
    return ""


@injected
async def __mock_cache():
    return ThreadPooledDictAsyncCache(src=dict())


@injected
async def injected_utils_default_serializer(data: Any) -> bytes:
    return jsonpickle.dumps(data).encode()


@injected
async def injected_utils_default_deserializer(data: bytes) -> Any:
    return jsonpickle.loads(data.decode())


__meta_design__ = design()
