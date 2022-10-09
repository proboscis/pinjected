from dataclasses import dataclass
from typing import Generic, TypeVar

from pinject_design.di.designed import Designed
from pinject_design.di.injected import Injected
from pinject_design.di.applicative import Applicative
from pinject_design.di.static_proxy import AstProxyContextImpl, Expr, eval_app

T = TypeVar("T")


@dataclass
class Sessioned(Generic[T]):
    """a value that holds designed instance, and evetually uses this designed to be run on the applied graph"""
    parent: "ExtendedObjectGraph"
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
    parent: "ExtendedObjectGraph"

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
    return eval_app(expr, app)


def sessioned_ast_context(session: "ExtendedObjectGraph"):
    app = ApplicativeSesionedImpl(session)
    return AstProxyContextImpl(
        lambda expr: eval_sessioned(expr, app),
        _alias_name="SessionedProxy"
    )
