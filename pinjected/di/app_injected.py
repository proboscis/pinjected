from dataclasses import dataclass
from typing import Set, Awaitable, TypeVar, Callable

from pinjected import Injected
from pinjected.di.applicative import Applicative
from pinjected.di.expr_util import Expr, Object, show_expr, UnaryOp, Call, BiOp, Attr, GetItem
from pinjected.di.injected import InjectedPure, InjectedFunction, InjectedByName
from pinjected.di.proxiable import T, DelegatedVar
from pinjected.di.static_proxy import eval_applicative, ast_proxy, \
    AstProxyContextImpl

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

    def _await_(self, tgt: Injected):
        async def awaiter(x):
            # from loguru import logger
            # logger.info(f"awaiting {x} due to await UnaryOp")
            res = await x
            # logger.info(f"obtained {res} for UnaryOp")
            return res

        return tgt.map(awaiter)


@dataclass
class EvaledInjected(Injected[T]):
    # TODO I think this class has issue with serialization of ast.
    value: Injected[T]
    ast: Expr[Injected[T]]

    def __post_init__(self):
        assert isinstance(self.ast, Expr)
        self.__expr__ = self.ast

    def dependencies(self) -> Set[str]:
        return self.value.dependencies()

    def get_provider(self):
        return self.value.get_provider()

    def __str__(self):
        #return f"EvaledInjected(value={self.value},ast={show_expr(self.ast, reduce_injected_expr)})"
        return f"Eval({show_expr(self.ast)})"

    def __repr__(self):
        return str(self)

    def repr_ast(self):
        return show_expr(self.ast, reduce_injected_expr)

    def __hash__(self):
        return hash((self.value, self.ast))

    def dynamic_dependencies(self) -> Set[str]:
        return self.value.dynamic_dependencies()

    def __repr_expr__(self):
        return show_expr(self.ast)



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


# class ApplicativeAsyncInjectedImpl(Applicative[Injected[Awaitable]]):
#     def map(self, target: Injected[Awaitable], f) -> T:
#         return AsyncMappedInjected(target, f)
#
#     def zip(self, *targets: Injected[Awaitable]):
#         return AsyncZippedInjected(*targets)
#
#     def pure(self, item) -> T:
#         match item:
#             case object(__is_awaitable__=True):
#                 return AsyncPureInjected(item)
#             case _:
#                 async def impl():
#                     return item
#
#                 return AsyncPureInjected(impl())
#
#     def is_instance(self, item) -> bool:
#         return isinstance(item, Injected)
#

def eval_injected(expr: Expr[Injected]) -> EvaledInjected:
    expr = await_awaitables(expr)
    return EvaledInjected(eval_applicative(expr, ApplicativeInjected), expr)
    # return EvaledInjected(eval_applicative(expr, ApplicativeAsyncInjected), expr)


def walk_replace(expr: Expr, transformer: Callable[[Expr], Expr]):
    memo = dict()
    from loguru import logger

    def impl(expr):
        match expr:
            case Object(DelegatedVar(Expr() as nested_expr, cxt) as dv):
                res = impl(nested_expr)
            case Object(x):
                res = transformer(Object(x))
            case Call(f, args, kwargs):
                res = transformer(
                    Call(
                        impl(f),
                        tuple([impl(a) for a in args]),
                        {k: impl(v) for k, v in kwargs.items()}
                    )
                )
            case BiOp(op, left, right):
                res = transformer(BiOp(op, impl(left), impl(right)))
            case UnaryOp(op, tgt):
                res = transformer(UnaryOp(op, impl(tgt)))
            case Attr(data, name):
                res = transformer(Attr(impl(data), name))
            case GetItem(data, key):
                res = transformer(GetItem(impl(data), impl(key)))
            case _:
                res = expr
        return res

    return impl(expr)


def await_awaitables(expr: Expr[T]) -> Expr:
    from loguru import logger
    # logger.info(f"await_awaitables {expr}")

    def transformer(expr: Expr):
        match expr:
            case Object(object(__is_awaitable__=True)):
                return UnaryOp('await', expr)
            case Call(Object(object(__is_async_function__=True)), args, kwargs) as call:
                return UnaryOp('await', call)
            case Call(object(__is_async_function__=True), args, kwargs) as call:
                return UnaryOp('await', call)
            case _:
                return expr

    return walk_replace(expr, transformer)




def injected_proxy(injected: Injected) -> DelegatedVar[Injected]:
    return ast_proxy(Object(injected), InjectedEvalContext)


class InjectedIter:
    def __init__(self, e):
        self.e = e
        self.i = 0

    def __iter__(self):
        return self

    def __next__(self):
        res = self.e[self.i]
        self.i += 1
        return res


def injected_iter_impl(e: Expr):
    return InjectedIter(e)


ApplicativeInjected = ApplicativeInjectedImpl()
# ApplicativeAsyncInjected = ApplicativeAsyncInjectedImpl()
InjectedEvalContext = AstProxyContextImpl(eval_injected, _alias_name="InjectedProxy")
