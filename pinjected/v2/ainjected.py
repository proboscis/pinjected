import abc
import asyncio
import inspect
from abc import ABC
from typing import Generic, TypeVar, Callable, Awaitable

T = TypeVar("T")


class AInjected(Generic[T], ABC):

    @property
    @abc.abstractmethod
    def dependencies(self) -> set[str]:
        pass

    @property
    @abc.abstractmethod
    def dynamic_dependencies(self) -> set[str]:
        pass

    @property
    def complete_dependencies(self) -> set[str]:
        return self.dependencies | self.dynamic_dependencies

    @abc.abstractmethod
    def get_provider(self) -> Callable[[...], Awaitable[T]]:
        pass

    @staticmethod
    def zip(*targets: 'AInjected'):
        return ZippedAInjected(*targets)

    def map(self, f: Callable[[T], Awaitable[T]]):
        assert inspect.iscoroutinefunction(f), f"f must be a coroutine function, got {f}"
        return MappedAInjected(self, f)

    @staticmethod
    def dict(**kwargs: 'AInjected'):
        async def mapper(vs):
            return dict(zip(kwargs.keys(), vs))
        return ZippedAInjected(*kwargs.values()).map(mapper)


class MappedAInjected(AInjected):
    def __init__(self, src: AInjected, f: Callable[[T], Awaitable[T]]):
        super().__init__()
        self.src = src
        self.f = f

    def dependencies(self) -> set[str]:
        return self.src.dependencies

    def dynamic_dependencies(self) -> set[str]:
        return self.src.dynamic_dependencies

    def get_provider(self) -> Callable[[...], Awaitable[T]]:
        coro_provider = self.src.get_provider()

        async def impl(**kwargs):
            result = await coro_provider(**kwargs)
            return await self.f(result)

        return impl


class ZippedAInjected(AInjected):
    def __init__(self, *srcs: AInjected):
        super().__init__()
        self.srcs = srcs

    def dependencies(self) -> set[str]:
        return {d for src in self.srcs for d in src.dependencies}

    def dynamic_dependencies(self) -> set[str]:
        return {d for src in self.srcs for d in src.dynamic_dependencies}

    def get_provider(self) -> Callable[[...], Awaitable[T]]:
        async def impl(**kwargs):
            tasks = []
            for p in self.srcs:
                deps = {d: kwargs[d] for d in p.dependencies}
                tasks.append(p.get_provider()(**deps))
            return await asyncio.gather(*tasks)

        return impl


class PureAInjected(AInjected):
    def __init__(self, src: Awaitable[T]):
        super().__init__()
        self.src = src

    def dependencies(self) -> set[str]:
        return set()

    def dynamic_dependencies(self) -> set[str]:
        return set()

    def get_provider(self) -> Callable[[...], Awaitable[T]]:
        async def impl(**kwargs):
            return await self.src

        return impl
