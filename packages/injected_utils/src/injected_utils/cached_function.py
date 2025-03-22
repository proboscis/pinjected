import asyncio
import base64
import datetime
import os
import pickle
from abc import ABC, abstractmethod, ABCMeta
from collections import defaultdict
from dataclasses import dataclass, field
from threading import Lock, RLock
from typing import Callable, Dict, Any, Union, Awaitable

import cloudpickle
from frozendict import frozendict
from sqlitedict import SqliteDict

import inspect
from returns.maybe import Nothing, Maybe, Some

from injected_utils.picklability_checker import assert_picklable
from injected_utils.shelf_util import MyShelf
from pinjected import Injected
from pinjected.di.proxiable import DelegatedVar
from pinjected.di.util import check_picklable
from loguru import logger


class IStringKeyProtocol(ABC):
    @abstractmethod
    def get_cache_key(self, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def encode_key(self, key):
        raise NotImplementedError

    @abstractmethod
    def decode_key(self, key):
        raise NotImplementedError


@dataclass
class StringKeyProtocol(IStringKeyProtocol):
    signature: inspect.Signature
    serializer: Callable[[Any], bytes] = field(default=pickle.dumps)
    deserializer: Callable[[bytes], Any] = field(default=pickle.loads)

    def get_cache_key(self, *args, **kwargs):
        # merge args and kwargs into kwargs using func's definition
        bound = self.signature.bind(*args, **kwargs)
        bound.apply_defaults()
        key = self.encode_key(frozendict(bound.arguments))
        return key

    def encode_key(self, key):
        return base64.b64encode(self.serializer(frozendict(key))).decode("utf-8")

    def decode_key(self, key):
        return self.deserializer(base64.b64decode(key.encode("utf-8")))


@dataclass
class ProtocolWrappedDict:
    protocol: StringKeyProtocol
    cache: Dict

    def __getitem__(self, item):
        return self.cache[self.protocol.encode_key(item)]

    def __setitem__(self, key, value):
        self.cache[self.protocol.encode_key(key)] = value

    def __contains__(self, item):
        return self.protocol.encode_key(item) in self.cache

    def __iter__(self):
        return iter(self.cache)

    def __len__(self):
        return len(self.cache)

    def __delitem__(self, key):
        del self.cache[self.protocol.encode_key(key)]

    def keys(self):
        return [self.protocol.decode_key(s) for s in self.cache.keys()]

    def items(self):
        return [(self.protocol.decode_key(k), v) for k, v in self.cache.items()]

@dataclass
class CachedFunction:
    """
    Stores both inputs and outputs.
    """
    cache: Dict
    func: Callable
    # This is a hack to make sure that the cache is picklable
    cache_serializer: Maybe = field(default=Nothing)
    cache_deserializer: Maybe = field(default=Nothing)
    # we need another protocol to encode/decode the value
    protocol: IStringKeyProtocol = field(default=None)
    lock: RLock = field(default_factory=RLock)

    def __post_init__(self):
        sig = inspect.signature(self.func)
        # funcの引数が*varargs（可変長引数）のみを持つことを確認
        assert len(sig.parameters) == 1 and list(sig.parameters.values())[0].kind == inspect.Parameter.VAR_POSITIONAL, \
            f"func must have only *args parameter, but got {sig}"
            
        self.cache_type = type(self.cache)
        if self.protocol is None:
            self.protocol: IStringKeyProtocol = StringKeyProtocol(
                sig,
                serializer=pickle.dumps,
                deserializer=pickle.loads
            )
        self.cache_locks = defaultdict(Lock)

    def _get_func_name(self):
        if hasattr(self.func, "__name__"):
            return self.func.__name__
        if hasattr(self.func, "__class__"):
            return self.func.__class__.__name__
        if hasattr(self.func, "__call__"):
            return self.func.__call__.__name__
        else:
            raise RuntimeError("cannot get function name")

    def __call__(self, *args, **kwargs):
        key = self.protocol.get_cache_key(*args, **kwargs)
        t = datetime.datetime.now()
        from loguru import logger
        # it's that we'll have futures that are waiting on the same key.
        args_repr = [repr(a)[:100] for a in args]
        args_repr += [f"{k}={v!r}" for k, v in kwargs.items()]
        assert isinstance(self.cache_locks, defaultdict)
        # logger.info(f"waiting for a lock:{key[:100]}")
        with self.get_key_lock(key):
            # logger.info(f"obtained a lock:{key[:100]}")
            if key in self.cache:
                # logger.debug(f"{self._get_func_name()}: cache hit for {args_repr}")
                try:
                    res = self.cache[key]
                    return res
                except Exception as e:
                    logger.warning(f"failed to load cache for {args_repr}")
                # logger.debug(f"cache hit for {args_repr} took {(datetime.datetime.now() - t).total_seconds()} seconds")
            else:
                # release lock and then compute
                logger.debug(f"{self._get_func_name()}: cache miss for {args_repr}")
            result = self.func(*args, **kwargs)
            self.cache[key] = result
            logger.debug(f"cache miss for {args_repr} took {(datetime.datetime.now() - t).total_seconds()} seconds")
            return result

    def get_key_lock(self, key):
        with self.lock:
            return self.cache_locks[key]

    def keys(self):
        return [self.protocol.decode_key(s) for s in self.cache.keys()]

    def __delitem__(self, key):
        key = self.ensure_key_type(key)
        with self.lock:
            del self.cache[key]

    def __contains__(self, item):
        key = self.ensure_key_type(item)
        with self.lock:
            return key in self.cache

    def ensure_key_type(self, item):
        if isinstance(item, frozendict):
            key = self.protocol.encode_key(item)
        elif isinstance(item, str):
            key = item
        else:
            raise TypeError("item must be frozendict or str")
        return key

    def __getstate__(self):
        state = (
            self.func,
            self.cache_serializer.value_or(lambda x: x)(self.cache),
            self.cache_type,
            self.cache_serializer,
            self.cache_deserializer,
            self.protocol,
        )
        assert_picklable(state)
        return state

    def __setstate__(self, state):
        self.func, cache, self.cache_type, self.cache_serializer, self.cache_deserializer, self.protocol = state
        self.cache = self.cache_deserializer.value_or(lambda x: x)(cache)
        self.cache_locks = defaultdict(Lock)
        assert isinstance(self.cache,
                          self.cache_type), f"{self.cache} is not {self.cache_type}. {cache}, {self.cache_type},{self.cache_deserializer}"

    def __getitem__(self, item):
        key = self.ensure_key_type(item)
        with self.lock:
            return self.cache[key]

    @staticmethod
    def create_with_shelf(path, func, serializer=Nothing, deserializer=Nothing):
        shelf = MyShelf(path, serializer, deserializer)
        return CachedFunction(shelf, func)

    @staticmethod
    def create_with_sqlite(path, func, serializer=Nothing, deserializer=Nothing):
        # sqlitedict is not picklable for ray.
        # one solution is to use RemoteInterpreter
        encode = serializer.value_or(lambda x: x)
        decode = deserializer.value_or(lambda x: x)
        from loguru import logger
        logger.info(f"creating sqlite dict at {path}")
        logger.info(f"current working dir is {os.getcwd()}")
        shelf = SqliteDict(path, encode=encode, decode=decode, autocommit=True)
        cache_serializer = Some(lambda sd: sd.filename)
        cache_deserializer = Some(lambda filename: SqliteDict(filename, encode=encode, decode=decode, autocommit=True))
        return CachedFunction(shelf, func, cache_serializer, cache_deserializer)

    @staticmethod
    def create_with_proxy(rif: "RemoteInterpreterFactory", gen_cache: Callable[[], Dict], func):
        env = rif.create(num_cpus=0)
        r_cache = env.put(gen_cache)()
        return CachedFunction(RemoteDict(r_cache), func)


@dataclass
class TimeCachedFunction:
    func: Callable
    cache_life: datetime.timedelta
    cache: Dict = field(default_factory=dict)
    lock: Lock = field(default_factory=Lock)

    def __post_init__(self):
        self.protocol = StringKeyProtocol(inspect.signature(self.func))

    def __call__(self, *args, **kwargs):
        from loguru import logger
        t = datetime.datetime.now()
        key = self.protocol.get_cache_key(*args, **kwargs)
        with self.lock:
            if key in self.cache:
                time, value = self.cache[key]
                dt = t - time
                if dt < self.cache_life:
                    logger.debug(f"cache hit for {args} {kwargs}")
                    logger.debug(f"cache hit for {args} {kwargs} took {datetime.datetime.now() - t}")
                    return value
            value = self.func(*args, **kwargs)
            self.cache[key] = (t, value)
            logger.debug(f"cache miss for {args} {kwargs} took {datetime.datetime.now() - t}")
            return value

    def __getstate__(self):
        return (
            self.func,
            self.cache_life,
            self.cache,
        )

    def __setstate__(self, state):
        self.func, self.cache_life, self.cache = state


def encode_base64_cloudpickle_str(d):
    return base64.b64encode(cloudpickle.dumps(d)).decode('utf-8')


def decode_base64_cloudpickle_str(s):
    return cloudpickle.loads(base64.b64decode(s.encode('utf-8')))


def no_change(func):
    async def impl(*args, **kwargs):
        return func(*args, **kwargs)

    return impl


class IKeyEncoder(metaclass=ABCMeta):
    @abstractmethod
    def get_key(self, *args, **kwargs):
        pass


@dataclass
class KeyEncoder(IKeyEncoder):
    signature: inspect.Signature
    key_serializer: Callable[[Any], str] = field(default=encode_base64_cloudpickle_str)

    def _encode_key(self, key) -> str:
        try:
            # this is incosistent across process. why is it?
            encoded = self.key_serializer(key)
            assert isinstance(encoded, str), f"key_serializer must return str. {encoded} is {type(encoded)}"
            return encoded
        except Exception as e:
            from loguru import logger
            logger.error(e)
            check_picklable(key)
            raise e

    def get_key(self, *args, **kwargs):
        bound = self.signature.bind(*args, **kwargs)
        bound.apply_defaults()

        key = self._encode_key(frozendict(bound.arguments))
        assert key is not None, f'key is None. {args},{kwargs}'
        return key


@dataclass
class AsyncLockMap:
    locks: Dict[Any, Lock] = field(default_factory=dict)

    def get(self,key):
        if key not in self.locks:
            self.locks[key] = asyncio.Lock()
        return self.locks[key]

class CacheValidationError(Exception):
    def __init__(self,
                 name:str,
                 args:tuple,
                    kwargs:dict,
                 function:Callable,
                 validator:Callable,
                 msg:str):
        super().__init__(msg)
        self.name = name
        self.args = args
        self.kwargs = kwargs
        self.function = function
        self.validator = validator

@dataclass
class AsyncCachedFunction:
    cache: Dict
    func: Callable
    en_async: "func -> async_func" = field(default=no_change)
    value_serializer: Union[Callable[[Any], bytes], None] = field(default=None)
    value_deserializer: Union[Callable[[bytes], Any], None] = field(default=None)
    # key_serializer: Callable[[Any], str] = field(default=encode_base64_cloudpickle_str)
    key_encoder: KeyEncoder = field(default=None)
    key_deserializer: Union[Callable[[str], Any], None] = field(default=decode_base64_cloudpickle_str)
    name: str = field(default=None)
    value_invalidator: Callable[[Any], Union[bool, Awaitable[bool]]] = field(default=lambda x: False)
    _concurrent_validation_count: int = field(default=0)
    _lock_map:AsyncLockMap = field(default_factory=AsyncLockMap)

    def __post_init__(self):
        from loguru import logger
        logger.info(f"async cached function created with cache: {self.cache}")
        assert not isinstance(self.cache, (Injected, DelegatedVar)), f"cache must be a dict, not {type(self.cache)}"
        if self.name is None:
            self.name = self.func.__name__
        assert isinstance(self.name, str), f"name must be str, not {type(self.name)}"
        if self.en_async is None:
            self.en_async = no_change
        if self.key_encoder is None:
            self.key_encoder = KeyEncoder(inspect.signature(self.func))

    async def _load_value(self, key):

        def impl():
            decoder = self.value_deserializer or (lambda x: x)
            start = datetime.datetime.now()
            res = decoder(self.cache[key])
            end = datetime.datetime.now()
            # logger.debug(f"cache load took {(end - start).total_seconds()} seconds")
            return res

        return await self.en_async(impl)()

    async def _write_value(self, key, value):
        def impl():
            encoder = self.value_serializer or (lambda x: x)
            self.cache[key] = encoder(value)

        await self.en_async(impl)()

    async def _invalidate_value(self, value) -> str:
        from loguru import logger
        # self._concurrent_validation_count += 1
        # logger.debug(f"invalidation start. {self._concurrent_validation_count} validations. {self.cache}")
        validation = self.value_invalidator(value)  # calling ray.remote doesn't stop .
        if inspect.isawaitable(validation):
            validation = await validation
        # this doesnt seem to be the bottle neck? the number of running validations are always 1.
        # logger.debug(f"invalidation end.   {self._concurrent_validation_count} validations. {self.cache}")
        # self._concurrent_validation_count -= 1
        match validation:
            case str():
                logger.warning(f"invalidated cache for {self.name}! {validation}")
                return validation
            case bool():
                return validation
            case None:
                return ""

        return validation

    async def __call__(self, *args, **kwargs):
        key = self.key_encoder.get_key(*args, **kwargs)
        invalidated = False
        async with self._lock_map.get(key):
            if key in self.cache:
                # logger.debug(f"async cached function hit for {self.name}! {str(args)[:100]}...,{str(kwargs)}...")
                try:
                    loaded = await self._load_value(key)
                    try:
                        if invalidated := await self._invalidate_value(loaded):
                            logger.warning(
                                f"invalidated a loaded cache for {self.name}! {str(args)[:100]}...,{str(kwargs)}...")
                        else:
                            return loaded
                    except Exception as validation_error:
                        logger.error(f"error while validating the decoded value")
                        raise validation_error
                except Exception as e:
                    logger.warning(f"error decoding cache for {self.name}:{key} {e}")
                    logger.warning(f"cache: {self.cache}")
                    logger.warning(f"cache key: {key}")
            if key in self.cache:
                logger.warning(f"cache hit but invalidated for {self.name}! {str(args)[:100]}...,{str(kwargs)}...")
            if not isinstance(self.cache, dict):
                logger.info(f"cache miss for {self.name}: {str(args)[:100]}...,{str(kwargs)[:100]}... in {self.cache}")
            try:
                result = await self.func(*args, **kwargs)  # this still has image_data in args
            except Exception as e:
                # import traceback
                # trb = "\n".join(traceback.format_exception(e))
                # logger.warning(
                #     f"error {type(e)}{e} when running impl:{self.func} for cache {self.name}! {str(args)[:100]}...,{str(kwargs)[:100]}... => not saving\n{trb}"
                # )
                raise e
            # logger.info(f"obtained result for {self.name}: {str(args)[:100]}...,{str(kwargs)[:100]}...")
            if cause := await self._invalidate_value(result):
                raise CacheValidationError(self.name, args, kwargs, self.func, self.value_invalidator, cause)
            if invalidated:
                logger.info(
                    f"cache was invalidated and is now valid for {self.name}: {str(args)[:100]}...,{str(kwargs)[:100]}...")
            await self._write_value(key, result)
            if not isinstance(self.cache, dict):
                logger.info(f"cache written for {self.name}: {str(args)[:100]}...,{str(kwargs)[:100]}...")
            return result

    def keys(self):
        return [self.decode_key(s) for s in self.cache.keys()]

    def decode_key(self, key: str):
        if self.key_deserializer is None:
            raise RuntimeError("key_deserializer is None. so key retrieval is not possible.")
        return self.key_deserializer(key)


@dataclass
class RemoteDict:
    src: "Var"#[Dict]

    def __getitem__(self, item):
        return self.src[item].fetch()

    def __setitem__(self, key, value):
        self.src[key] = value

    def __contains__(self, item):
        return item in self.src

    def __delitem__(self, key):
        del self.src[key]

    def keys(self):
        # wait, keys maybe an iterator, so... return all keys at once?
        # or shall we iterate while fetching?
        # lets go for iteration,,, since we are not sure which is the over head.
        # but keys are usually small, so it should be fine.
        return self.src.env.put(lambda x: list(x.keys()))(self.src).fetch()

    def values(self):
        for v in self.src.values():
            yield v.fetch()

    def items(self):
        for pair in self.src.items():
            yield pair.fetch()
