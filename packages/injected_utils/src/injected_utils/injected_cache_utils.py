import asyncio
import hashlib
import inspect
import threading
import time
from asyncio import Future
from collections.abc import Callable
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path
from pprint import pformat
from typing import Any, ParamSpec

import cloudpickle
import filelock
import jsonpickle
import pandas as pd
from frozendict import frozendict
from returns.maybe import Some
from sqlitedict import SqliteDict

from injected_utils.cached_function import (
    AsyncCachedFunction,
    CachedFunction,
    IKeyEncoder,
    IStringKeyProtocol,
    KeyEncoder,
)
from pinjected import *
from pinjected import Injected, injected, instance
from pinjected.decoration import update_if_registered
from pinjected.di.metadata.bind_metadata import BindMetadata
from pinjected.di.proxiable import DelegatedVar
from pinjected.di.util import get_code_location
from pinjected.providable import Providable

try:
    from pinjected import AsyncResolver
except ImportError:
    from pinjected.v2.resolver import AsyncResolver

# from data_tree.util import Pickled

P = ParamSpec("P")
Hasher = Callable[[P], Any]
HasherFactory = Callable[[inspect.Signature], Hasher]


def ensure_injected(i: Providable):
    match i:
        case str():
            return injected(i)
        case Injected():
            return i
        case type():
            return Injected.bind(i)
        case DelegatedVar():
            return i.eval()
        case f if isinstance(f, Callable):
            return Injected.bind(i)
        case _:
            raise ValueError(f"cannot convert {i} to Injected")


def pickled_injected(cache_path, injected: Injected):
    from data_tree.util import Pickled

    injected = ensure_injected(injected)

    def _impl(__resolver__: AsyncResolver):
        return Pickled(
            cache_path,
            lambda: __resolver__.to_blocking()[injected],
            backend=cloudpickle,
        ).value

    return (
        Injected.bind(_impl)
        .add_dynamic_dependencies(*injected.complete_dependencies)
        .proxy
    )


@instance
@dataclass
class AsyncRunTracker:
    logger: "Logger"

    def __post_init__(self):
        self.running_tasks = []
        self.bound = self.logger.bind(name="AsyncRunTracker")

    def log_status(self):
        self.bound.info(
            f"running tasks: {pformat([i[1] for i in self.running_tasks])}\n num:{len(self.running_tasks)}"
        )

    def register(self, fut: Future, fn, *args, **kwargs):
        self.bound.info(f"adding {fn} to running tasks")
        self.log_status()
        self.running_tasks.append((fut, fn, args, kwargs))

        def done(fut):
            self.bound.info(f"removing {fn} from running tasks")
            self.running_tasks.remove((fut, fn, args, kwargs))
            self.log_status()

        fut.add_done_callback(done)


@injected
async def async_run(thread_pool, AsyncRunTracker, /, fn, *args, **kwargs):
    # Ah, there are 391 tasks submitted
    # logger.info(f"submitting to thread pool {fn} from {threading.current_thread()}")
    # assert threading.current_thread().name == "MainThread", f"current thread is {threading.current_thread()}"
    fut = thread_pool.submit(fn, *args, **kwargs)
    # logger.info(f"awaiting {fn} to thread pool")
    wrapped = asyncio.wrap_future(fut)
    AsyncRunTracker.register(wrapped, fn, args, kwargs)
    res = await wrapped
    # logger.info(f"got result from thread pool")
    # logger.info(f"remaining tasks: {RUNNING_TASKS[:1]} num:{len(RUNNING_TASKS)} ")

    return res


@injected
async def run_in_new_thread(fn, /, *args, **kwargs):
    res = Future()
    import threading

    def run_task():
        from loguru import logger

        # holy fuck loguru!
        try:
            logger.info(f"running {fn} in new thread :{threading.current_thread()}")
            data = fn(*args, **kwargs)
            logger.info(f"finished {fn} in new thread :{threading.current_thread()}")
            res.set_result(data)
        except Exception as e:
            res.set_exception(e)

    thread = threading.Thread(target=run_task)
    from loguru import logger

    logger.info(f"starting thread {thread} for {fn}")
    thread.start()
    try:
        logger.info(f"waiting for thread {thread} for {fn}")
        await asyncio.sleep(1)  # sleeping here for 1 sec fixes the problem. but why?
        logger.info(f"waiting for thread {thread} for {fn} 2...")
        return await res
    except Exception as e:
        logger.error(f"error in run_in_new_thread: {e}")
        raise e


def provide_cached(cache, async_run, func: Callable, additional_key: Injected):
    from loguru import logger

    async def task(key, *args, **kwargs):
        return await async_run(func, *args, **kwargs)

    assert not isinstance(func, DelegatedVar), f"func is DelegatedVar: {func}"
    assert not isinstance(func, Injected)

    cached = AsyncCachedFunction(
        cache,
        task,
        value_serializer=cloudpickle.dumps,
        value_deserializer=cloudpickle.loads,
        key_serializer=lambda obj: sha256(jsonpickle.dumps(obj).encode()).hexdigest(),
        key_deserializer=None,
        name=func.__name__,
    )

    async def interface(*args, **kwargs):
        logger.info(f"cached called with: {func.__name__, args, kwargs}")
        # here it does have image_path available in args
        return await cached(additional_key, *args, **kwargs)

    return interface


def default_key_encoder(func):
    return KeyEncoder(
        inspect.signature(func),
        key_serializer=lambda obj: sha256(jsonpickle.dumps(obj).encode()).hexdigest(),
    )


def provide_cached_async(
    cache,
    async_func,
    additonal_key,
    en_async,
    value_invalidator=lambda x: False,
    key_encoder_factory: Callable[[inspect.Signature], KeyEncoder] = None,
):
    """
    TODO: Fix for issue #217 - @async_cached decorator does not respect key_hashers parameter

    Problem:
    - The key_hashers parameter is not properly used because CustomKeyHasher receives the wrong signature
    - The wrapper function signature (added_key, *args, **kwargs) is passed instead of the original function signature
    - This prevents proper mapping of parameter names to their custom hashers

    Fix Plan:
    1. In provide_cached_async (line ~208):
       - Change: key_encoder = key_encoder_factory(inspect.signature(task))
       - To: key_encoder = key_encoder_factory(task.__original_signature__)

    2. In CustomKeyHasher.calc_cache_key (line ~540):
       - Update the method to handle the signature mismatch properly
       - Extract added_key from the first argument
       - Use the original signature to bind remaining args/kwargs
       - Apply key_hashers based on the original parameter names

    3. Add tests to verify:
       - key_hashers are properly applied to named parameters
       - Both positional and keyword arguments work correctly
       - The cache key changes when using different hashers

    Implementation steps:
    - [x] Update provide_cached_async to pass original signature
    - [x] Refactor CustomKeyHasher.calc_cache_key to handle signature mismatch
    - [x] Add unit tests for the fix
    - [x] Update documentation if needed

    Status: COMPLETED - Fix implemented and tested successfully
    """

    async def task(added_key, *args, **kwargs):
        return await async_func(*args, **kwargs)

    task.__original_signature__ = inspect.signature(async_func)
    # task.__defined_frame__ = defined_frame
    task.__name__ = async_func.__name__
    if key_encoder_factory is not None:
        key_encoder = key_encoder_factory(task.__original_signature__)
    else:
        key_encoder = default_key_encoder(task)

    cached = AsyncCachedFunction(
        cache,
        task,
        en_async=en_async,
        value_serializer=cloudpickle.dumps,
        value_deserializer=cloudpickle.loads,
        # key_serializer=lambda obj: sha256(jsonpickle.dumps(obj).encode()).hexdigest(),
        key_encoder=key_encoder,
        key_deserializer=None,
        name=async_func.__name__,
        value_invalidator=value_invalidator,
    )

    async def interface(*args, **kwargs):
        return await cached(additonal_key, *args, **kwargs)

    return interface


@injected
def to_async(async_run, /, func):
    async def task(*args, **kwargs):
        return await async_run(func, *args, **kwargs)

    return task


def run_async(func: Injected[Callable]):
    func = ensure_injected(func)
    return to_async(func).eval()


def en_async_cached(cache: Injected[dict], *additional_keys: Injected):
    """
    decorator for an InjectedFunction to be run with a cache and a thread pool.
    :param cache:
    :param additional_key: additional key to be used for the cache key.
    :return:
    """
    additional_key = Injected.mzip(*[ensure_injected(i) for i in additional_keys])

    def _impl(func: Injected[Callable]):
        from loguru import logger

        assert isinstance(func, Injected)
        logger.info(f"en_async_cached called with: {func}")
        return Injected.bind(
            provide_cached, cache=cache, func=func, additional_key=additional_key
        )

    return _impl


@dataclass
class HasherKeyEncoder(IKeyEncoder):
    hasher: Hasher

    def get_key(self, *args, **kwargs):
        key = self.hasher(*args, **kwargs)
        serialized = cloudpickle.dumps(key)
        # TODO hash the key so that it won't consume too much storage space in case the object is very big.
        return hashlib.sha256(serialized).hexdigest()
        # breturn serialized


def async_cached(
    cache: Injected[dict],
    *additional_key: Injected,
    en_async=None,
    value_invalidator=None,
    hasher_factory: Injected[HasherFactory] = None,
    key_hashers: Injected[dict[str, callable]] = None,
    replace_binding=True,
):
    """
    非同期関数の結果をキャッシュするためのデコレータファクトリです。

    このデコレータは、非同期関数の結果をキャッシュし、同じ入力に対する再計算を避けることで
    パフォーマンスを最適化します。キャッシュキーの生成方法をカスタマイズでき、
    値の無効化条件も指定できます。

    Parameters
    ----------
    cache : Injected[Dict]
        キャッシュストアとして使用する辞書オブジェクト
    *additional_key : Injected
        キャッシュキーに追加で含める値。複数指定可能
    en_async : Optional
        非同期実行の制御オプション。デフォルトはNone
    value_invalidator : Optional[Callable]
        キャッシュ値を無効化するための関数。デフォルトはNone
    hasher_factory : Optional[Injected[HasherFactory]]
        キャッシュキーの生成方法をカスタマイズするファクトリ関数
    key_hashers : Optional[Injected[dict[str, callable]]]
        引数名ごとにハッシュ関数を指定する辞書
    replace_binding : bool
        デコレータが適用された関数のバインディングを置き換えるかどうか。デフォルトはTrue

    Returns
    -------
    Callable
        非同期関数をデコレートする関数

    Example
    -------
    ```python
    @async_cached(my_cache, version_key)
    @injected
    async def fetch_data(client, /, user_id: str):
        return await client.get_user_data(user_id)
    ```

    Notes
    -----
    - デコレートされた関数の引数は全てキャッシュキーの一部として使用されます
    - hasher_factoryとkey_hashersは排他的で、両方同時には使用できません
    - キャッシュキーはデフォルトでJSONPickleでシリアライズされSHA-256ハッシュ化されます
    """
    additional_key = Injected.mzip(*[ensure_injected(i) for i in additional_key])
    parent_frame = inspect.currentframe().f_back

    from loguru import logger

    logger.debug(f"async_cached called with key_hashers: {key_hashers}")

    # logger.info(f"async_cached called in {parent_frame.f_code.co_filename}:{parent_frame.f_lineno}")
    if hasher_factory is not None:

        def provide_factory(_factory: HasherFactory):
            def factory(signature: inspect.Signature):
                hasher: Hasher = _factory(signature)
                key_encoder = HasherKeyEncoder(hasher)
                return key_encoder

            return factory

        key_encoder_factory = Injected.bind(provide_factory, _factory=hasher_factory)
    elif key_hashers is not None:

        def provide_key_hasher(_key_hashers: dict[str, callable]):
            def factory(signature: inspect.Signature):
                key_hasher = dict()
                for key, hasher in _key_hashers.items():
                    key_hasher[key] = hasher
                hasher = CustomKeyHasher(signature, key_hasher)
                return HasherKeyEncoder(hasher)

            return factory

        key_encoder_factory = Injected.bind(
            provide_key_hasher, _key_hashers=key_hashers
        )
    else:
        key_encoder_factory = Injected.pure(None)

    def impl(async_func: Injected[Callable]):
        res = Injected.bind(
            provide_cached_async,
            en_async=Injected.pure(None) if en_async is None else en_async,
            cache=cache,
            async_func=async_func,
            additonal_key=additional_key,
            value_invalidator=Injected.pure(lambda x: False)
            if value_invalidator is None
            else value_invalidator,
            key_encoder_factory=key_encoder_factory,
        )
        res.__is_async_function__ = True
        if replace_binding:
            return update_if_registered(
                async_func,
                res,
                Some(BindMetadata(code_location=Some(get_code_location(parent_frame)))),
            )
        return res

    return impl


@dataclass
class PicklableSqliteDict:
    src: SqliteDict

    def __reduce__(self):
        return PicklableSqliteDict.from_path, (self.src.filename,)

    @classmethod
    def from_path(cls, path):
        if isinstance(path, str):
            path = Path(path)
        assert isinstance(path, Path), f"path must be a Path object, but got {path}"
        path.parent.mkdir(parents=True, exist_ok=True)
        return cls(SqliteDict(path, autocommit=True))

    def __getitem__(self, item):
        return self.src[item]

    def __setitem__(self, key, value):
        self.src[key] = value

    def __contains__(self, item):
        return item in self.src

    def __delitem__(self, instance):
        del self.src[instance]


@dataclass
class JsonBackedSqliteDict:
    src: SqliteDict

    def __reduce__(self):
        return JsonBackedSqliteDict.from_path, (self.src.filename,)

    @classmethod
    def from_path(cls, path):
        return cls(SqliteDict(path, autocommit=True))

    def __getitem__(self, item):
        key = jsonpickle.dumps(item)
        return jsonpickle.loads(self.src[key])

    def __setitem__(self, key, value):
        key = jsonpickle.dumps(key)
        value = jsonpickle.dumps(value)
        self.src[key] = value

    def __contains__(self, item):
        key = jsonpickle.dumps(item)
        return key in self.src

    def __delitem__(self, instance):
        key = jsonpickle.dumps(instance)
        del self.src[key]

    def values(self):
        return [jsonpickle.loads(v) for v in self.src.values()]

    def keys(self):
        return [jsonpickle.loads(k) for k in self.src.keys()]


@injected
def sqlite_cache(cache_path: str | Path):
    # TODO wrap this to be serializable for the ray.
    return PicklableSqliteDict.from_path(cache_path)


@injected
def sqlite_dict(cache_path: str | Path):
    Path(cache_path).parent.mkdir(parents=True, exist_ok=True)
    return JsonBackedSqliteDict.from_path(cache_path)


@injected
def sqlite_dict_with_backup(cache_path: str | Path, backup_frequency: pd.Timedelta):
    """
    periodically
    :param cache_path:
    :param backup_frequency:
    :return:
    """
    cache = JsonBackedSqliteDict.from_path(cache_path)
    cache_path = Path(cache_path)
    backup_path = cache_path.with_suffix(".backup")
    timestamp_path = cache_path.with_suffix(".timestamp")
    backup_lock = filelock.FileLock(str(cache_path) + ".lock")

    def save_backup():
        # shutil.copy(cache_path, tmp_path) # this is to prevent the file from being corrupted.
        # shutil.move(tmp_path, backup_path)
        import os

        from loguru import logger

        os.system(f"rsync -a {cache_path} {backup_path}")
        logger.info(f"backed up {cache_path} to {backup_path}")
        backup_time = pd.Timestamp.now()
        timestamp_path.write_text(backup_time.isoformat())

    # we need some way to know when it's being called....
    def backup_task():
        while True:
            with backup_lock:
                if timestamp_path.exists():
                    last_backup = pd.Timestamp(timestamp_path.read_text())
                else:
                    last_backup = pd.Timestamp.now()
                if pd.Timestamp.now() - last_backup > backup_frequency:
                    save_backup()
                time.sleep(30)

    backup_thread = threading.Thread(target=backup_task, daemon=True)
    backup_thread.start()

    return cache


@dataclass
class CustomKeyHasher:
    signature: inspect.Signature
    key_hasher: dict[str, Callable[[Any], Any]] = field(default_factory=dict)
    type_hasher: dict[type, Callable[[Any], Any]] = field(default_factory=dict)

    def __call__(self, *args, **kwargs):
        return self.calc_cache_key(*args, **kwargs)

    def calc_cache_key(self, *args, **kwargs):
        """
        Fix for issue #217 - Handle signature mismatch properly
        ✓ COMPLETED
        
        This method now correctly handles the signature mismatch where it receives 
        (added_key, *args, **kwargs) but self.signature is the original function signature.
        
        Implementation:
        1. Extract added_key from args[0]
        2. Create a new binding using self.signature with args[1:] and kwargs
        3. Apply key_hasher and type_hasher to the correctly mapped parameters
        4. Include added_key in the final cache key
        
        Example:
        - Original function: async def fetch_data(user_id: str, include_details: bool)
        - Called as: calc_cache_key(added_key_value, "user123", include_details=True)
        - Maps correctly: user_id="user123", include_details=True
        - Applies hashers based on these parameter names
        """
        # Extract added_key from the first argument
        if not args:
            raise ValueError("calc_cache_key expects at least one argument (added_key)")

        added_key = args[0]
        actual_args = args[1:]

        from loguru import logger

        logger.debug(
            f"CustomKeyHasher.calc_cache_key called with signature: {self.signature}"
        )
        logger.debug(
            f"Added key: {added_key}, actual args: {actual_args}, kwargs: {kwargs}"
        )
        logger.debug(f"Key hashers: {self.key_hasher}")

        # Bind the actual arguments to the original function signature
        try:
            bound = self.signature.bind(*actual_args, **kwargs)
            bound.apply_defaults()
        except TypeError as e:
            # Fallback to old behavior if binding fails
            # This maintains backward compatibility
            logger.warning(
                f"Failed to bind arguments to signature: {e}. Using fallback method."
            )

            # Old implementation for backward compatibility
            bound = inspect.signature(lambda added_key, *args, **kwargs: None).bind(
                *args, **kwargs
            )
            bound.apply_defaults()
            encoded_dict = {}
            kwargs = bound.arguments["kwargs"]
            encoded_kwargs = {}
            for key, v in kwargs.items():
                if key in self.key_hasher:
                    encoded_kwargs[key] = self.key_hasher[key](v)
                elif type(v) in self.type_hasher:
                    encoded_kwargs[key] = self.type_hasher[type(v)](v)
                else:
                    encoded_kwargs[key] = v
            encoded_dict["added_key"] = bound.arguments["added_key"]
            encoded_dict["args"] = bound.arguments["args"]
            encoded_dict["kwargs"] = frozendict(encoded_kwargs)
            encoded_dict = frozendict(encoded_dict)
            return cloudpickle.dumps(encoded_dict)

        # Apply key_hasher and type_hasher to the bound arguments
        encoded_dict = {}
        for param_name, value in bound.arguments.items():
            if param_name in self.key_hasher:
                hashed_value = self.key_hasher[param_name](value)
                logger.debug(f"Hashing {param_name}={value} -> {hashed_value}")
                encoded_dict[param_name] = hashed_value
            elif type(value) in self.type_hasher:
                hashed_value = self.type_hasher[type(value)](value)
                logger.debug(f"Type hashing {param_name}={value} -> {hashed_value}")
                encoded_dict[param_name] = hashed_value
            else:
                encoded_dict[param_name] = value

        # Create the final cache key including the added_key
        final_key = {"added_key": added_key, "params": frozendict(encoded_dict)}

        logger.debug(f"Final cache key structure: {final_key}")

        return cloudpickle.dumps(frozendict(final_key))

    def encode_key(self, key):
        if key in self.key_hasher:
            return self.key_hasher[key](key)
        if type(key) in self.type_hasher:
            return self.type_hasher[type(key)](key)
        return key


default_custom_key_hasher_factory = Injected.pure(CustomKeyHasher)


@injected
def custom_key_hasher_factory(
    key_hasher: dict[str, callable] = None,
    type_hasher: dict[type, callable] = None,
):
    """
    Use this factory along with @sync_cached to provide custom key hasher.
    :param key_hasher:
    :param type_hasher:
    :return:
    """

    def impl(signature: inspect.Signature):
        params = dict()
        if key_hasher is not None:
            params["key_hasher"] = key_hasher
        if type_hasher is not None:
            params["type_hasher"] = type_hasher
        return CustomKeyHasher(signature=signature, **params)

    return impl


@dataclass
class HasherKeyProtocolAdapter(IStringKeyProtocol):
    hasher: Hasher

    def __call__(self, *args, **kwargs):
        return self.hasher(*args, **kwargs)

    def get_cache_key(self, *args, **kwargs):
        return self.hasher(*args, **kwargs)

    def encode_key(self, key):
        raise NotImplementedError

    def decode_key(self, key):
        raise NotImplementedError


def sync_cached(
    cache: Injected[dict],
    *deps: Injected,
    hasher_factory: Injected[HasherFactory] = default_custom_key_hasher_factory,
):
    """
    Decorator factory for synchronously caching the output of functions.

    This function is designed to be used as a higher-order function that takes a cache object,
    dependencies, and an optional hasher factory. It returns a decorator that when applied to a
    function, enables caching of its outputs based on computed hash keys of the input arguments.

    Parameters:
    - cache (Injected[Dict]): An Injected type wrapper around a dictionary that acts as the cache store.
    - *deps (Injected): Zero or more Injected type dependencies that the function may rely on. These are
      included in the cache key computation.
    - hasher_factory (Injected[HasherFactory], optional): An Injected type wrapper around a factory that
      creates Hasher objects. Defaults to `default_custom_key_hasher_factory` if not provided.

    The decorated function will check the cache before execution and return the cached result if available.
    If the result is not in the cache, it will execute the function, cache its result, and then return it.

    The decorator is intended to be used in environments where function calls are expensive and results
    are deterministic, allowing for significant performance optimizations.

    Returns:
    - A decorator function that can be applied to another function to enable caching.

    Example:
    ```
    @sync_cached(my_cache, dep1, dep2,)
    @injected
    def my_expensive_function(injected_deps1,/,arg1, arg2):
        # injected_deps1 will not used for keys
        # Function implementation
        pass
    ```

    The decorator created by `sync_cached` will manage caching for `my_expensive_function` based on its
    arguments `arg1` and `arg2`, and the dependencies `dep1` and `dep2`.
    """
    cache = ensure_injected(cache)
    deps = [ensure_injected(d) for d in deps]
    parent_frame = inspect.currentframe().f_back

    def provide_blocking_cache(cache, func, _deps, _hasher_factory):
        def new_impl(deps, *arg, **kwargs):
            from loguru import logger

            # deps are just for cache key purposes
            logger.info(f"new_impl called with: {func.__name__, arg, kwargs}")
            res = func(*arg, **kwargs)
            logger.info(f"new_impl returned: {res}")
            return res

        hasher: Hasher = _hasher_factory(inspect.signature(new_impl))

        cached = CachedFunction(
            cache,
            new_impl,
            cache_serializer=Some(cloudpickle.dumps),
            cache_deserializer=Some(cloudpickle.loads),
            protocol=HasherKeyProtocolAdapter(hasher),
            # key_serializer=lambda obj: sha256(jsonpickle.dumps(obj).encode()).hexdigest(),
            # key_deserializer=None
        )

        def interface(*arg, **kwargs):
            return cached(_deps, *arg, **kwargs)

        return interface

    def impl(func: Injected[Callable]):
        func = ensure_injected(func)
        res = Injected.bind(
            provide_blocking_cache,
            cache=cache,
            func=func,
            _deps=Injected.mzip(*deps),
            _hasher_factory=hasher_factory,
        )
        return update_if_registered(
            func,
            res,
            Some(BindMetadata(code_location=Some(get_code_location(parent_frame)))),
        )

    return impl


def blocking_cached(
    cache: Injected[dict],
    *deps: Injected,
    protocol: Injected[IStringKeyProtocol] = None,
):
    """
    decorator for an InjectedFunction to be run with a cache.
    :param cache:
    :param deps: these are for cache key purposes
    :return:
    """

    cache = ensure_injected(cache)
    deps = [ensure_injected(d) for d in deps]
    parent_frame = inspect.currentframe().f_back

    def provide_blocking_cache(cache, func, _deps, _protocol):
        def new_impl(deps, *arg, **kwargs):
            # deps are just for cache key purposes
            return func(*arg, **kwargs)

        cached = CachedFunction(
            cache,
            new_impl,
            cache_serializer=Some(cloudpickle.dumps),
            cache_deserializer=Some(cloudpickle.loads),
            protocol=_protocol,
            # key_serializer=lambda obj: sha256(jsonpickle.dumps(obj).encode()).hexdigest(),
            # key_deserializer=None
        )

        def interface(*arg, **kwargs):
            return cached(_deps, *arg, **kwargs)

        return interface

    injected_protocol = Injected.pure(None) if protocol is None else protocol

    def impl(func: Injected[Callable]):
        func = ensure_injected(func)
        res = Injected.bind(
            provide_blocking_cache,
            cache=cache,
            func=func,
            _deps=Injected.mzip(*deps),
            _protocol=injected_protocol,
        )
        return update_if_registered(
            func,
            res,
            Some(BindMetadata(code_location=Some(get_code_location(parent_frame)))),
        )

    return impl


def parse_preference_assignments(res: dict):
    """
    Parse the preference assignments from the response of Amazon Mech Turk.
    :param res:
    :return:
    """


__meta_design__ = design(
    overrides=design(
        injected_utils_default_hasher=lambda item: sha256(
            jsonpickle.dumps(item).encode()
        ).hexdigest()
    )
)
