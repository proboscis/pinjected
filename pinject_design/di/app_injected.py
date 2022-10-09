from dataclasses import dataclass
from typing import Set

from pinject_design import Injected
from pinject_design.di.applicative import Applicative
from pinject_design.di.injected import InjectedPure
from pinject_design.di.proxiable import T, DelegatedVar
from pinject_design.di.static_proxy import Expr, Object, eval_app, ast_proxy, \
    show_expr, AstProxyContextImpl


class ApplicativeInjectedImpl(Applicative[Injected]):

    def map(self, target: Injected, f) -> T:
        return target.map(f)

    def zip(self, *targets: Injected):
        return Injected.mzip(*targets)

    def pure(self, item) -> T:
        return Injected.pure(item)
    def is_instance(self, item) ->bool:
        return isinstance(item,Injected)


def reduce_injected_expr(expr: Expr):
    match expr:
        case Object(InjectedPure(value)):
            return str(value)
        case Object(Injected() as i):
            return f"{i.__class__.__name__}()"


@dataclass
class EvaledInjected(Injected[T]):
    value: Injected[T]
    ast: Expr[Injected[T]]

    def dependencies(self) -> Set[str]:
        return self.value.dependencies()

    def get_provider(self):
        return self.value.get_provider()

    def __str__(self):
        return f"EvaledInjected(value={self.value},ast={show_expr(self.ast, reduce_injected_expr)})"
    def __repr__(self):
        return str(self)


def eval_injected(expr: Expr[Injected]) -> EvaledInjected:
    return EvaledInjected(eval_app(expr, ApplicativeInjected), expr)


def injected_proxy(injected: Injected) -> DelegatedVar[Injected]:
    return ast_proxy(injected, InjectedEvalContext)


ApplicativeInjected = ApplicativeInjectedImpl()
InjectedEvalContext = AstProxyContextImpl(eval_injected, _alias_name="InjectedProxy")
