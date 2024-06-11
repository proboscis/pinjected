import abc
import asyncio
import inspect
from abc import ABC
from dataclasses import dataclass, field, replace
from typing import Generic, Dict, Any, Callable, Awaitable, TypeVar

from returns.maybe import Maybe, Nothing, Some

from pinjected import Injected
from pinjected.di.app_injected import EvaledInjected
from pinjected.di.metadata.bind_metadata import BindMetadata
from pinjected.v2.keys import IBindKey, StrBindKey
from pinjected.v2.provide_context import ProvideContext

T = TypeVar('T')
U = TypeVar('U')


class IBind(Generic[T], ABC):
    """
    hold a provider and metadata
    """

    @abc.abstractmethod
    async def provide(self, cxt: ProvideContext, deps: Dict[IBindKey, Any]) -> T:
        pass

    @property
    @abc.abstractmethod
    def dependencies(self) -> set[IBindKey]:
        pass

    @property
    @abc.abstractmethod
    def dynamic_dependencies(self) -> set[IBindKey]:
        pass

    @property
    def complete_dependencies(self) -> set[IBindKey]:
        return self.dependencies | self.dynamic_dependencies

    def amap(self, async_func):
        assert inspect.iscoroutinefunction(async_func), f"async_func must be a coroutine function, got {async_func}"
        return MappedBind(self, async_func)

    @staticmethod
    def zip(*targets: 'IBind'):
        deps = {d for t in targets for d in t.dependencies}

        async def impl(cxt, deps: dict):
            tasks = []
            for t in targets:
                tasks.append(t.provide(cxt, {k: deps[k] for k in t.dependencies}))
            return await asyncio.gather(*tasks)

        return JustBind(impl, deps)

    def map(self, func):
        assert not inspect.iscoroutinefunction(func), f"func must not be a coroutine function, got {func}"

        async def async_func(data):
            return func(data)

        return self.amap(async_func)

    @staticmethod
    def dict(**targets: 'IBind'):
        async def mapper(data):  # data is a tuple of results
            return {k: v for k, v in zip(targets.keys(), data)}

        return IBind.zip(*targets).amap(mapper)

    @staticmethod
    def list(*targets: 'IBind'):
        async def mapper(data):
            return list(data)

        return IBind.zip(*targets).amap(mapper)

    @property
    @abc.abstractmethod
    def metadata(self) -> Maybe[BindMetadata]:
        raise NotImplementedError("metadata must be implemented")

    @abc.abstractmethod
    def update_metadata(self, metadata: BindMetadata) -> "IBind":
        raise NotImplementedError("update_metadata must be implemented")


@dataclass
class JustBind(IBind[T]):
    impl: Callable[[ProvideContext, Dict[IBindKey, Any]], Awaitable[T]]
    deps: set[IBindKey]

    async def provide(self, cxt: ProvideContext, deps: Dict[IBindKey, Any]) -> T:
        return await self.impl(cxt, deps)

    @property
    def dependencies(self) -> set[IBindKey]:
        return self.deps


@dataclass
class StrBind(IBind[T]):
    """
    most basic binding that uses strings as keys.
    """
    impl: Callable[[...], Awaitable[T]]
    deps: set[str]

    def __post_init__(self):
        self.keys = {StrBindKey(d) for d in self.deps}

    async def provide(self, cxt: ProvideContext, deps: Dict[IBindKey, Any]) -> T:
        dep_dict = {d.name: deps[d] for d in self.keys}
        return await self.impl(**dep_dict)

    @property
    def dependencies(self) -> set[IBindKey]:
        return {StrBindKey(d) for d in self.deps}

    @classmethod
    def pure(cls, value: T) -> 'StrBind[T]':
        async def impl():
            return value

        return cls(impl, set())

    @classmethod
    def async_bind(cls, func: Callable[..., Awaitable[T]]) -> 'StrBind[T]':
        # assert inspect.iscoroutinefunction(func), f"func must be a coroutine function, got {func}"
        deps = inspect.signature(func).parameters.keys()
        return cls(func, set(deps))

    @classmethod
    def func_bind(cls, func: Callable[..., T]) -> 'StrBind[T]':
        assert not inspect.iscoroutinefunction(func), f"func must be ordinal function, got {func}"

        async def impl(**kwargs):
            return func(**kwargs)

        deps = inspect.signature(func).parameters.keys()
        return cls(impl, set(deps))

    @classmethod
    def bind(cls, func: Callable[..., T]) -> 'StrBind[T]':
        if inspect.iscoroutinefunction(func):
            return cls.async_bind(func)
        else:
            return cls.func_bind(func)


@dataclass
class BindInjected(IBind[T]):
    src: Injected
    _metadata: Maybe[BindMetadata] = field(default=Nothing)

    def __post_init__(self):
        assert isinstance(self.src, Injected), f"src must be an Injected, got {self.src}"

    async def provide(self, cxt: ProvideContext, deps: Dict[IBindKey, Any]) -> T:
        from loguru import logger
        keys = {StrBindKey(d) for d in self.src.dependencies()}
        dep_dict = {d.name: deps[d] for d in keys}
        func = self.src.get_provider()
        logger.trace(f"provider:{func}")
        assert inspect.iscoroutinefunction(
            func), f"provider of an Injected({self.src}) must be a coroutine function, got {func}"
        data = await func(**dep_dict)
        # assert not inspect.isawaitable(data), f"provider of an Injected({self.src}) must return a non-awaitable, got {data}"
        return data

    @property
    def dependencies(self) -> set[IBindKey]:
        return {StrBindKey(d) for d in self.src.dependencies()}

    @property
    def dynamic_dependencies(self) -> set[IBindKey]:
        return {StrBindKey(d) for d in self.src.dynamic_dependencies()}

    @property
    def metadata(self) -> Maybe[BindMetadata]:
        return self._metadata

    def update_metadata(self, metadata: BindMetadata) -> "IBind":
        return replace(self, _metadata=Some(metadata))


@dataclass
class ExprBind(IBind):
    src: EvaledInjected
    _metadata: Maybe[BindMetadata] = field(default=Nothing)

    @property
    def dependencies(self) -> set[IBindKey]:
        return {StrBindKey(d) for d in self.src.dependencies()}

    @property
    def dynamic_dependencies(self) -> set[IBindKey]:
        return {StrBindKey(d) for d in self.src.dynamic_dependencies()}

    @property
    def metadata(self) -> Maybe[BindMetadata]:
        return self._metadata

    def update_metadata(self, metadata: BindMetadata) -> "IBind":
        return replace(self, _metadata=Some(metadata))

    def __post_init__(self):
        assert isinstance(self.src, EvaledInjected), f"src must be an Expr, got {self.src}"

    async def provide(self, cxt: ProvideContext, deps: Dict[IBindKey, Any]) -> T:
        return await cxt.resolver._provide_providable(self.src)


@dataclass
class MappedBind(IBind[U]):
    src: IBind[T]
    async_f: Callable[[T], Awaitable[U]]

    async def provide(self, cxt: ProvideContext, deps: Dict[IBindKey, Any]) -> T:
        data = self.src.provide(cxt, deps)
        return await self.async_f(data)

    @property
    def dependencies(self) -> set[IBindKey]:
        return self.src.dependencies


