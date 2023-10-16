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

    @abc.abstractmethod
    def dependencies(self) -> set[IBindKey]:
        pass

    def amap(self, async_func):
        assert inspect.iscoroutinefunction(async_func), f"async_func must be a coroutine function, got {async_func}"
        return MappedBind(self, async_func)

    @staticmethod
    def zip(*targets: 'IBind'):
        deps = {d for t in targets for d in t.dependencies()}

        async def impl(cxt, deps: dict):
            tasks = []
            for t in targets:
                tasks.append(t.provide(cxt, {k: deps[k] for k in t.dependencies()}))
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
class MappedBind(IBind[U]):
    src: IBind[T]
    async_f: Callable[[T], Awaitable[U]]

    async def provide(self, cxt: ProvideContext, deps: Dict[IBindKey, Any]) -> T:
        data = self.src.provide(cxt, deps)
        return await self.async_f(data)

    def dependencies(self) -> set[IBindKey]:
        return self.src.dependencies()


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


@dataclass
class AsyncResolver:
    blueprint: Blueprint
    objects: Dict[IBindKey, Any] = field(default_factory=dict)

    async def provide(self, key: IBindKey, cxt: ProvideContext):
        logger.info(f"providing {key}")
        if key not in self.objects:
            tasks = []
            bind = self.blueprint.bindings[key]
            dep_keys = list(bind.dependencies())
            for key in dep_keys:
                n_cxt = ProvideContext(key=key, parent=cxt)
                tasks.append(self.provide(key, n_cxt))
            res = await asyncio.gather(*tasks)
            deps = dict(zip(dep_keys, res))
            self.objects[key] = await bind.provide(cxt, deps)
        return self.objects[key]


Providable = Union[str, IBindKey, Callable]


@dataclass
class Resolver:
    resolver: AsyncResolver

    def provide(self, tgt: Providable):
        cxt = ProvideContext(key=StrBindKey(tgt), parent=None)
        return asyncio.run(self.resolver.provide(cxt.key, cxt))


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


@injected
async def z(x, y, /, ):
    await asyncio.sleep(0.1)
    return x + y


@injected
async def test(z, /):
    item = await z()
    logger.info(f"z:{item}")
    return item


@instance  # @instance async def return a CachedAwaitable object
async def test3(z):
    return await z()


# so, test3 is a CachedAwaitable and must be awaited.
# this means that things from original Design must be awaited.
async def provide_test2(test3):
    return await test3


bp = providers(
    test2=provide_test2  # async providers work fine in blueprint
) + d_instances(
    x='x',
    y='y'
) + d_providers(
    z=z,
    test=test,
    test3=test3,
    test4=test3
)


# we can use async_bind on @instance to make it work.
async def wait(t):
    return await t


Resolver(AsyncResolver(bp)).provide('test4')  # calling test returns a coroutine, which is a correct behavior.
# TODO fix things annotated in @instance to return object rather than coroutine.
# also, the providers needs to omit awaits.
# %%
# In order to fully switch to async design, I need to ...
"""
1. implement visualizer -> 3 hours
2. implement partial injection annotator -> 3 hours
3. implement run_main with meta-design -> 1 day
4. implement plugins  -> 3 hours
-> total 2 days of work. hmm....
"""
