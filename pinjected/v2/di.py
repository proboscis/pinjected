import abc
import asyncio
import inspect
from abc import ABC
from dataclasses import dataclass, field
from typing import Generic, TypeVar, Dict, Any, Optional, Callable, Awaitable, Union

from loguru import logger

from pinjected import Injected, Design, injected, instance
from pinjected import instances as d_instances
from pinjected import providers as d_providers
from pinjected.di.implicit_globals import IMPLICIT_BINDINGS
from test.test_to_script import src

T = TypeVar('T')
U = TypeVar('U')


@dataclass
class ProvideContext:
    key: Optional['IBindKey']
    parent: Optional['ProvideContext']

    @property
    def trace(self):
        if self.parent is None:
            return []
        else:
            return self.parent.trace + [self]


class IBindKey(ABC):
    """
    hold a providing key and metadata
    """
    pass


@dataclass(frozen=True)
class StrBindKey(IBindKey):
    name: str


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
        # assert inspect.iscoroutinefunction(self.impl), f"impl must be an coroutine function, got {self.impl}"
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
class StrBindInjected(IBind[T]):
    src: Injected

    async def provide(self, cxt: ProvideContext, deps: Dict[IBindKey, Any]) -> T:
        dep_dict = {d.name: deps[d] for d in self.keys}
        func = self.src.get_provider()
        match func:
            case object(__is_awaitable__=True):
                data = await func(**dep_dict)
            case x:
                data = func(**dep_dict)
        return data

    @property
    def dependencies(self) -> set[IBindKey]:
        return {StrBindKey(d) for d in self.src.dependencies()}


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


class _Injected(Generic[T]):
    """

    """


@dataclass(frozen=True)
class Blueprint:
    bindings: Dict[IBindKey, IBind]

    def __add__(self, other):
        match other:
            case Design():
                return self + design_to_blueprint(other)
            case Blueprint():
                return Blueprint(self.bindings | other.bindings)
            case _:
                raise TypeError(f"Blueprint can only be added with Blueprint or Design, got {other}")

    def blocking_resolver(self):
        return AsyncResolver(self).to_blocking()

    def async_resolver(self):
        return AsyncResolver(self)


Providable = Union[str, IBindKey, Callable, IBind]


@dataclass
class AsyncResolver:
    blueprint: Blueprint
    objects: Dict[IBindKey, Any] = field(default_factory=dict)

    def __post_init__(self):
        self.objects = {
            StrBindKey("__resolver__"): self,
            StrBindKey("__blueprint__"): self.blueprint,
        }

    async def _provide(self, key: IBindKey, cxt: ProvideContext):
        logger.info(f"providing {key}")
        if key not in self.objects:
            tasks = []
            bind = self.blueprint.bindings[key]
            dep_keys = list(bind.dependencies)
            for key in dep_keys:
                n_cxt = ProvideContext(key=key, parent=cxt)
                tasks.append(self._provide(key, n_cxt))
            res = await asyncio.gather(*tasks)
            deps = dict(zip(dep_keys, res))
            self.objects[key] = await bind.provide(cxt, deps)
        return self.objects[key]

    async def _provide_providable(self, tgt: Providable):
        async def resolve_deps(keys: set[IBindKey]):
            tasks = [self._provide(k, ProvideContext(key=k, parent=None)) for k in keys]
            return {k: v for k, v in zip(keys, await asyncio.gather(*tasks))}

        match tgt:
            case str():
                return await self._provide(StrBindKey(tgt), ProvideContext(key=StrBindKey(tgt), parent=None))
            case IBindKey():
                return await self._provide(tgt, ProvideContext(key=tgt, parent=None))
            case Callable():
                deps = inspect.signature(tgt).parameters.keys()
                keys = {StrBindKey(d) for d in deps}
                deps = {k: await self._provide(k, ProvideContext(key=k, parent=None)) for k in keys}
                data = tgt(**deps)
                if inspect.iscoroutinefunction(tgt):
                    return await data
                else:
                    return data
            case IBind():
                deps = await resolve_deps(tgt.dependencies)
                return await tgt.provide(ProvideContext(key=tgt, parent=None), deps)
            case _:
                raise TypeError(f"tgt must be str, IBindKey, Callable or IBind, got {tgt}")

    async def provide(self, tgt: Providable):
        return await self._provide_providable(tgt)

    def to_blocking(self):
        return Resolver(self)

    def __getitem__(self, item):
        return self.provide(item)


@dataclass
class Resolver:
    resolver: AsyncResolver

    def provide(self, tgt: Providable):
        return asyncio.run(self.resolver.provide(tgt))

    def to_async(self):
        return self.resolver

    def __getitem__(self, item):
        return self.provide(item)


def instances(**kwargs):
    return Blueprint({StrBindKey(k): StrBind.pure(v) for k, v in kwargs.items()})


def providers(**kwargs: Callable[..., Union[T, Awaitable[T]]]):
    return Blueprint({StrBindKey(k): StrBind.bind(v) for k, v in kwargs.items()})


def injected_to_str_bind(injected: Injected):
    match injected:
        case object(__is_awaitable__=True):
            return StrBind.async_bind(injected.get_provider())
        case x:
            return StrBind.bind(injected.get_provider())


def design_to_blueprint(design: Design):
    bindings = IMPLICIT_BINDINGS | design.bindings
    return Blueprint({StrBindKey(k): injected_to_str_bind(v.to_injected()) for k, v in bindings.items()})


# %%
"""
TODO make blueprint from a design
by default ,convert the Injected into async func.
"""


@instance
async def slow_1():
    logger.info(f"running slow_1")
    await asyncio.sleep(1)
    logger.info(f"slow_1 done")
    return 1


@instance
async def slow_data():
    logger.info(f"running slow_data")
    await asyncio.sleep(1)
    logger.info(f"slow_data done")
    return 1


@instance
async def slow_calc(slow_data, slow_1):
    return slow_data + slow_1


@instance
def blocking_x(slow_data, slow_1):
    return slow_data + slow_1


bp = providers(
) + d_instances(
    x='x',
    y='y'
) + d_providers(
    slow_1=slow_1,
    slow_data=slow_data
)


# we can use async_bind on @instance to make it work.
async def wait(t):
    return await t


bp.blocking_resolver().provide('blocking_x')
# %%
# In order to fully switch to async design, I need to ...
"""
1. implement visualizer -> 3 hours
2. implement partial injection annotator -> 3 hours
3. implement run_main with meta-design -> 1 day
4. implement plugins  -> 3 hours
-> total 2 days of work. hmm....

Wait isnt this already done???
You can just use the Injected, you implemented already.
Right, and call async_resolver().provide() to get the result.
"""
