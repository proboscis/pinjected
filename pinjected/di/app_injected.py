from dataclasses import dataclass
from loguru import logger
from typing import Set

from pinjected import Injected
from pinjected.di.applicative import Applicative
from pinjected.di.injected import InjectedPure, InjectedFunction, InjectedByName
from pinjected.di.proxiable import T, DelegatedVar
from pinjected.di.static_proxy import eval_applicative, ast_proxy, \
    AstProxyContextImpl
from pinjected.di.ast import Expr, Object, show_expr


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


def eval_injected(expr: Expr[Injected]) -> EvaledInjected:
    return EvaledInjected(eval_applicative(expr, ApplicativeInjected), expr)


def injected_proxy(injected: Injected) -> DelegatedVar[Injected]:
    return ast_proxy(injected, InjectedEvalContext)


ApplicativeInjected = ApplicativeInjectedImpl()
InjectedEvalContext = AstProxyContextImpl(eval_injected, _alias_name="InjectedProxy")
