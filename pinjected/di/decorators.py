import inspect
from typing import Union, Callable

from returns.maybe import Some

from pinjected import Injected
from pinjected.di.implicit_globals import IMPLICIT_BINDINGS
from pinjected.di.injected import PartialInjectedFunction
from pinjected.di.util import get_code_location
import functools
import asyncio


def injected_function(f, parent_frame=None) -> PartialInjectedFunction:
    """
    any args starting with "_" or positional_only kwargs is considered to be injected.
    :param f:
    :return:
    """
    # How can we make this work on a class method?
    sig: inspect.Signature = inspect.signature(f)
    tgts = dict()
    if parent_frame is None:
        parent_frame = inspect.currentframe().f_back
    for k, v in sig.parameters.items():
        # does this contain self?
        # assert k != 'self', f"self is not allowed in injected_function... for now:{f}"
        #
        if k.startswith("_"):
            tgts[k] = Injected.by_name(k[1:])
        elif v.kind == inspect.Parameter.POSITIONAL_ONLY:
            tgts[k] = Injected.by_name(k)
    new_f = Injected.partial(f, **tgts)

    from pinjected.di.bindings import InjectedBind
    from pinjected.di.bindings import BindMetadata
    IMPLICIT_BINDINGS[f.__name__] = InjectedBind(
        new_f,
        metadata=Some(BindMetadata(code_location=Some(get_code_location(parent_frame)))),
    )

    return new_f


def injected_instance(f) -> Injected:
    # check f is an async function
    is_coroutine = inspect.iscoroutinefunction(f)
    if is_coroutine:
        f = cached_coroutine(f)

    sig: inspect.Signature = inspect.signature(f)
    tgts = {k: Injected.by_name(k) for k, v in sig.parameters.items()}
    instance = Injected.partial(f, **tgts)().eval()
    from pinjected.di.bindings import InjectedBind
    from pinjected.di.bindings import BindMetadata
    IMPLICIT_BINDINGS[f.__name__] = InjectedBind(
        instance,
        Some(BindMetadata(code_location=Some(get_code_location(inspect.currentframe().f_back))))
    )
    instance.__is_awaitable__ = is_coroutine
    return instance


def injected(tgt: Union[str, type, Callable]):
    if isinstance(tgt, str):
        return Injected.by_name(tgt).proxy
    elif isinstance(tgt, type):
        return injected_function(tgt, parent_frame=inspect.currentframe().f_back)
    elif callable(tgt):
        return injected_function(tgt, parent_frame=inspect.currentframe().f_back)


def injected_class(cls):
    return injected_function(cls)


def injected_method(f):
    _impl = injected_function(f)

    def impl(self, *args, **kwargs):
        return _impl(self, *args, **kwargs)

    return impl


class CachedAwaitable:
    def __init__(self, coro):
        self.coro = coro
        self._cache = None
        self._has_run = False
        self._lock = asyncio.Lock()

    def __await__(self):
        return self._get_result().__await__()

    async def _get_result(self):
        async with self._lock:
            if not self._has_run:
                self._cache = await self.coro
                self._has_run = True
        return self._cache


def cached_coroutine(coro_func):
    @functools.wraps(coro_func)
    def wrapper(*args, **kwargs):
        return CachedAwaitable(coro_func(*args, **kwargs))

    functools.update_wrapper(wrapper, coro_func)
    return wrapper


instance = injected_instance
