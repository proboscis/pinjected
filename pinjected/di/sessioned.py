from dataclasses import dataclass
from typing import Generic, TypeVar

from pinjected.di.designed import Designed
from pinjected.di.injected import Injected
from pinjected.di.applicative import Applicative
from pinjected.di.static_proxy import AstProxyContextImpl, eval_applicative
from pinjected.di.expr_util import Expr

T = TypeVar("T")


@dataclass
class Sessioned(Generic[T]):
    """a value that holds designed instance, and evetually uses this designed to be run on the applied graph"""
    parent: "IObjectGraph"
    designed: Designed[T]

    def map(self, f):
        return Sessioned(self.parent, self.designed.map(f))

    def zip(self,*others):
        new_d = Designed.zip(*[o.designed for o in [self] + list(others)])
        return Sessioned(self.parent, new_d)

    def run(self):
        return self.parent[self.designed]

    def run_sessioned(self):
        return self.parent.sessioned(self.designed)

    def override(self, design: "Design"):
        return Sessioned(self.parent, self.designed.override(design))

    @property
    def proxy(self):
        return self.parent.proxied(self.designed)


@dataclass
class ApplicativeSesionedImpl(Applicative[Sessioned]):
    parent: "IObjectGraph"

    def map(self, target: Sessioned, f) -> Sessioned:
        return target.map(f)

    def zip(self, *targets: Sessioned):
        if targets:
            return targets[0].zip(*targets[1:])
        else:
            return Sessioned(self.parent, Designed.bind(Injected.pure(())))


    def pure(self, item) -> Sessioned:
        return Sessioned(self.parent, Designed.bind(Injected.pure(item)))

    def is_instance(self, item) -> bool:
        return isinstance(item, Sessioned)


def eval_sessioned(expr: Expr[Sessioned], app: Applicative[Sessioned]) -> Sessioned:
    return eval_applicative(expr, app)


def sessioned_ast_context(session: "IObjectGraph"):
    app = ApplicativeSesionedImpl(session)
    return AstProxyContextImpl(
        lambda expr: eval_sessioned(expr, app),
        _alias_name="SessionedProxy"
    )
