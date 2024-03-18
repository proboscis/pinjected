import asyncio
from dataclasses import dataclass
from loguru import logger
from typing import Set, Awaitable, Callable, TypeVar, Tuple

from pinjected import Injected
from pinjected.di.applicative import Applicative
from pinjected.di.injected import InjectedPure, InjectedFunction, InjectedByName
from pinjected.di.proxiable import T, DelegatedVar
from pinjected.di.static_proxy import eval_applicative, ast_proxy, \
    AstProxyContextImpl
from pinjected.di.ast import Expr, Object, show_expr

U = TypeVar('U')


class ApplicativeInjectedImpl(Applicative[Injected]):

    def map(self, target: Injected, f) -> T:
        return target.map(f)

    def zip(self, *targets: Injected):
        return Injected.mzip(*targets)

    def pure(self, item) -> T:
        return Injected.pure(item)

    def is_instance(self, item) -> bool:
        return isinstance(item, Injected)


@dataclass
class EvaledInjected(Injected[T]):
    # TODO I think this class has issue with serialization of ast.
    value: Injected[T]
    ast: Expr[Injected[T]]

    def __post_init__(self):
        assert isinstance(self.ast, Expr)

    def dependencies(self) -> Set[str]:
        return self.value.dependencies()

    def get_provider(self):
        return self.value.get_provider()

    def __str__(self):
        return f"EvaledInjected(value={self.value},ast={show_expr(self.ast, reduce_injected_expr)})"

    def __repr__(self):
        return str(self)

    def repr_ast(self):
        return show_expr(self.ast, reduce_injected_expr)

    def __hash__(self):
        return hash((self.value, self.ast))

    def dynamic_dependencies(self) -> Set[str]:
        return self.value.dynamic_dependencies()


def reduce_injected_expr(expr: Expr):
    match expr:
        case Object(InjectedPure(value)):
            return str(value)
        case Object(InjectedFunction(func, kwargs)):
            reduced = reduce_injected_expr(Object(kwargs))
            return f"{func.__name__}({reduced})"
        case Object(DelegatedVar() as dv):
            return reduce_injected_expr(Object(dv.eval()))
        case Object(EvaledInjected() as ei):
            reduced = ei.repr_ast()
            return reduced
        case Object(InjectedByName(name)):
            return f"$('{name}')"
        case Object(Injected() as i):
            return f"<{i.__class__.__name__}>"


class ApplicativeAsyncInjectedImpl(Applicative[Injected[Awaitable]]):
    def map(self, target: Injected[Awaitable], f) -> T:
        return AsyncMappedInjected(target, f)

    def zip(self, *targets: Injected[Awaitable]):
        return AsyncZippedInjected(*targets)

    def pure(self, item) -> T:
        match item:
            case object(__is_awaitable__=True):
                return AsyncPureInjected(item)
            case _:
                async def impl():
                    return item

                return AsyncPureInjected(impl())

    def is_instance(self, item) -> bool:
        return isinstance(item, Injected)



class AsyncMappedInjected(Injected):

    # src: Injected[Awaitable[T]]
    # f: Callable[[T], Awaitable[U]]
    def __init__(self, src: Injected[Awaitable], f: Callable[[T], Awaitable[U]]):
        super().__init__()
        self.src = src
        self.f = f

    def dependencies(self) -> Set[str]:
        return self.src.dependencies()

    def dynamic_dependencies(self) -> Set[str]:
        return self.src.dynamic_dependencies()

    def get_provider(self):
        coro_provider = self.src.get_provider()

        async def impl(**kwargs):
            result = await coro_provider(**kwargs)
            return await self.f(result)

        return impl


class AsyncZippedInjected(Injected):
    # src:Tuple[Injected[Awaitable]]
    def __init__(self, *srcs: Injected[Awaitable]):
        super().__init__()
        self.srcs = srcs

    def dependencies(self) -> Set[str]:
        return {d for src in self.srcs for d in src.dependencies()}

    def dynamic_dependencies(self) -> Set[str]:
        return {d for src in self.srcs for d in src.dynamic_dependencies()}

    def get_provider(self):
        async def impl(**kwargs):
            tasks = []
            for p in self.srcs:
                deps = {d: kwargs[d] for d in p.dependencies()}
                logger.info(f"zipped deps: {deps}")
                tasks.append(p.get_provider()(**deps))
            return await asyncio.gather(*tasks)

        return impl


class AsyncPureInjected(Injected):
    # src:Awaitable[T]
    def __init__(self, src: Awaitable[T]):
        super().__init__()
        self.src = src

    def dependencies(self) -> Set[str]:
        return set()

    def dynamic_dependencies(self) -> Set[str]:
        return set()

    def get_provider(self):
        async def impl():
            return await self.src

        return impl


def eval_injected(expr: Expr[Injected]) -> EvaledInjected:
    #return EvaledInjected(eval_applicative(expr, ApplicativeInjected), expr)
    return EvaledInjected(eval_applicative(expr, ApplicativeAsyncInjected), expr)


def injected_proxy(injected: Injected) -> DelegatedVar[Injected]:
    return ast_proxy(injected, InjectedEvalContext)


ApplicativeInjected = ApplicativeInjectedImpl()
ApplicativeAsyncInjected = ApplicativeAsyncInjectedImpl()
InjectedEvalContext = AstProxyContextImpl(eval_injected, _alias_name="InjectedProxy")
