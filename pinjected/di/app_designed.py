from dataclasses import dataclass

from pinjected import Designed, Injected, Design
from pinjected.di.applicative import Applicative
from pinjected.di.designed import PureDesigned
from pinjected.di.injected import InjectedPure
from pinjected.di.proxiable import T, DelegatedVar
from pinjected.di.static_proxy import eval_applicative, ast_proxy, AstProxyContextImpl
from pinjected.di.expr_util import Expr, Object, show_expr


class ApplicativeDesignedImpl(Applicative[Designed]):

    def map(self, target: Designed, f) -> T:
        return target.map(f)

    def zip(self, *targets: Designed):
        return Designed.zip(*targets)

    def pure(self, item) -> T:
        return Designed.bind(Injected.pure(item))

    def is_instance(self, item) ->bool:
        return isinstance(item,Designed)


def reduce_designed_expr(expr: Expr):
    match expr:
        case Object(PureDesigned(design, InjectedPure(value))):
            return f"Object({str(value)} with {design})"


@dataclass
class EvaledDesigned(Designed[T]):
    value: Designed[T]
    ast: Expr[Designed[T]]

    @property
    def design(self) -> "Design":
        return self.value.design

    @property
    def internal_injected(self) -> "Injected":
        return self.value.internal_injected

    def __str__(self):
        return f"EvaledDesigned(value={self.value},ast={show_expr(self.ast, reduce_designed_expr)})"


def eval_designed(expr: Expr[Designed]) -> Designed:
    return EvaledDesigned(eval_applicative(expr, ApplicativeDesigned), expr)


def designed_proxy(designed: Designed) -> DelegatedVar[Designed]:
    return ast_proxy(designed, DesignedEvalContext)


ApplicativeDesigned = ApplicativeDesignedImpl()
DesignedEvalContext = AstProxyContextImpl(eval_designed, _alias_name="DesignedProxy")
