import shelve
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

from filelock import FileLock
from loguru import logger
from returns.maybe import Maybe, Nothing, Some

T = TypeVar("T")


@dataclass
class MyShelf(Generic[T]):
    # TODO use SqliteDict instead. shelf has issues with retrieving keys.
    path: str
    serializer: Maybe[Callable[[T], Any]] = field(default=Nothing)
    deserializer: Maybe[Callable[[Any], T]] = field(default=Nothing)
    lock: FileLock = field(default=None)

    def __post_init__(self):
        self.lock = FileLock(self.path + ".lock")
        logger.info(f"initialized MyShelf at {self.path}")

    def __setstate__(self, state):
        self.path, self.serializer, self.deserializer = state
        self.lock = FileLock(self.path + ".lock")

    def __getstate__(self):
        return self.path, self.serializer, self.deserializer

    def __getitem__(self, item):
        assert isinstance(item, str), f"key must be str, but got {item}"
        # logger.debug(f"waiting lock for getitem")
        with self.lock, shelve.open(self.path) as shelf:
            # logger.debug(f"obtained lock for getitem")
            try:
                value = self.deserializer.value_or(lambda x: x)(shelf[item])
                # logger.debug(f"value of {item} is {value}")
                return value
            except KeyError as e:
                logger.warning(
                    f"failed to load value of {item}, due to {e}, from {self.path}"
                )
                raise e
            except Exception as e:
                logger.error(
                    f"failed to load value of {item}, due to {type(e), e}, from {self.path}"
                )
                raise e
        # logger.debug(f"released lock for getitem")

    def __setitem__(self, key, value):
        assert isinstance(key, str), f"key must be str, but got {key}"
        # logger.debug(f"waiting lock for setitem")
        with self.lock, shelve.open(self.path) as shelf:
            # logger.debug(f"obtained lock for setitem")
            to_save = self.serializer.value_or(lambda x: x)(value)
            shelf[key] = to_save
            # make sure the data is deserializeable
            # but it seems this is done okey...
            self.deserializer.value_or(lambda x: x)(shelf[key])
        # logger.debug(f"released lock for setitem")

    def __contains__(self, item):
        assert isinstance(item, str), f"item must be str, but got {item}"
        # logger.debug(f"waiting lock for contains")
        with self.lock, shelve.open(self.path) as shelf:
            # logger.debug(f"obtained lock for contains")
            return item in shelf

    def keys(self):
        with self.lock, shelve.open(self.path) as shelf:
            for key in shelf:
                yield key

    def __delitem__(self, key):
        assert isinstance(key, str), f"key must be str, but got {key}"
        # logger.debug(f"waiting lock for delitem")
        with self.lock, shelve.open(self.path) as shelf:
            # logger.debug(f"obtained lock for delitem")
            del shelf[key]
        # logger.debug(f"released lock for delitem")

    def items(self):
        keys = list(self.keys())
        for k in keys:
            try:
                v = self[k]
                yield k, v
            except Exception as e:
                logger.error(f"failed to load value of {k}, due to {e}")
                del self[k]
                raise e

    def get_maybe(self, key):
        assert isinstance(key, str), f"key must be str, but got {key}"
        if key in self:
            return Some(self[key])
        return Nothing

    def clear(self):
        with self.lock, shelve.open(self.path) as shelf:
            # remove the file
            shelf.clear()
