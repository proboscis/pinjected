import abc
import asyncio
import os
import threading
from abc import ABC
from asyncio import Event
from dataclasses import dataclass
from pathlib import Path
from typing import Generic, TypeVar, Callable, Awaitable, Optional

import cloudpickle
from filelock import FileLock
from loguru import logger
from pinjected import Injected
from pinjected.compatibility.task_group import TaskGroup

try:
    from pinjected.v2.resolver import AsyncResolver
except ImportError:
    from pinjected import AsyncResolver


@dataclass
class AsyncFileLock:
    path: str

    def __post_init__(self):
        self.lock = FileLock(self.path)
        self.alock = asyncio.Lock()

    def __getstate__(self):
        return self.path

    def __setstate__(self, state):
        self.path = state
        self.lock = FileLock(state)
        self.alock = asyncio.Lock()

    async def __aenter__(self):
        logger.info(f"trying to acquire async lock before {self.path}")
        await self.alock.acquire()
        logger.success(f"acquired async lock before {self.path}")

        def acquire_task():
            logger.info(f'acquiring file lock at {self.path}')
            self.lock.acquire()
            logger.success(f'acquired file lock at {self.path}')

        await asyncio.get_event_loop().run_in_executor(None, acquire_task)

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await asyncio.get_event_loop().run_in_executor(None, self.lock.release)
        self.alock.release()


T = TypeVar('T')


class AsyncSerializationBackend(ABC):
    @abc.abstractmethod
    async def load(self, f):
        raise NotImplementedError

    @abc.abstractmethod
    async def dump(self, f, data):
        raise NotImplementedError


@dataclass
class ASBCloudpickle(AsyncSerializationBackend):
    async def load(self, f):
        return await asyncio.get_event_loop().run_in_executor(None, cloudpickle.load, f)

    async def dump(self, f, data):
        return await asyncio.get_event_loop().run_in_executor(None, cloudpickle.dump, data, f)


class AsyncPickled(Generic[T]):
    def __init__(
            self,
            path,
            proc: Callable[[], Awaitable[T]],
            backend: AsyncSerializationBackend = None,
            timeout_sec:Optional[float] = 10
    ):
        if backend is None:
            backend = ASBCloudpickle()
        self.timeout_sec = timeout_sec
        self.loaded = False
        self._value = None
        self.path = path
        self.proc = proc
        self.lock = AsyncFileLock(str(self.path) + ".lock")
        Path(self.lock.lock.lock_file).parent.mkdir(parents=True, exist_ok=True)
        self.backend = backend

    def __getstate__(self):
        state = dict(
            path=self.path,
            proc=self.proc,  # I think this is preventing pickling.. but it is a must to pickle this.
            backend=self.backend
        )
        # at this point self.proc requires recursive pickling
        return state

    def __setstate__(self, state):
        self.loaded = False
        self._value = None
        self.path = state["path"]
        self.proc = state["proc"]
        self.lock = AsyncFileLock(self.path + ".lock")
        self.backend = state['backend']

    @property
    async def value(self):
        from loguru import logger
        # logger.debug(f"cache value access from {callee}")
        logger.debug(f"{threading.current_thread().name}:trying to aqquire lock:{self.lock.path}")
        async with TaskGroup() as tg:
            acquired = Event()

            async def timeout_check():
                logger.info(f"waiting for cache lock for {self.timeout_sec} seconds...")
                await asyncio.wait_for(acquired.wait(), self.timeout_sec)
                logger.success(f"cache lock acquired!")
                # hmm, it doesn't rais exception???

            tg.create_task(timeout_check())

            async def write_task():

                async with self.lock:
                    from loguru import logger
                    acquired.set()
                    if not self.loaded:
                        logger.debug(f"{threading.current_thread().name}:aqquired lock:{self.lock.path}")
                        try:
                            with open(self.path, 'rb') as f:
                                data = await self.backend.load(f)
                                self._value = data
                        except Exception as e:
                            from loguru import logger
                            logger.warning(f"failed to load cache at {self.path} due to {e}")
                            data = await self.proc()
                            with open(self.path, 'wb') as f:
                                await self.backend.dump(f, data)
                                self._value = data
                        self.loaded = True

            tg.create_task(write_task())
        # logger.debug(f"{threading.current_thread().name}:released lock:{self.lock.path}")
        return self._value

    async def clear(self):
        from loguru import logger
        async with self.lock:
            try:
                await asyncio.get_event_loop().run_in_executor(None, os.remove, self.path)
                self.loaded = False
                logger.info(f"deleted pickled file at {self.path}")
            except FileNotFoundError as e:
                self.loaded = False
                logger.warning(f"no cache found at {self.path}")


def pickled(cache_path, injected: Injected):
    injected = Injected.ensure_injected(injected)

    async def _impl(__resolver__: AsyncResolver):
        async def __impl():
            return await __resolver__[injected]

        return await AsyncPickled(cache_path, __impl).value

    return Injected.bind(_impl).add_dynamic_dependencies(*injected.complete_dependencies).proxy
