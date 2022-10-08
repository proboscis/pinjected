from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Generic, Tuple, Dict, Any, Callable, Optional, Iterator, Set

from cytoolz import valmap
from frozendict import frozendict

from pinject_design import Injected, Designed, Design
from pinject_design.di.designed import PureDesigned
from pinject_design.di.injected import InjectedPure
from pinject_design.di.proxiable import T, DelegatedVar, IProxyContext


class Expr(Generic[T]):
    def __getattr__(self, item: str):
        return Attr(self, item)

    def _wrap_if_non_expr(self,item)->"Self":
        if not isinstance(item,Expr):
            return Object(item)
        else:
            return item

    def __call__(self, *args: "Expr", **kwargs: "Expr"):
        return Call(self,
                    tuple(self._wrap_if_non_expr(item) for item in args),
                    {k:self._wrap_if_non_expr(v) for k,v in kwargs.items()}
                    )

    def __getitem__(self, item: "Expr"):
        return GetItem(self, self._wrap_if_non_expr(item))

    def __str__(self):
        return f"Expr(||{show_expr(self)}||)"

    def __repr__(self):
        return str(self)

#from pydantic import BaseModel
#@dataclass(frozen=True)
from attr import define
from attr import field as a_field
@define
class Call(Expr[T]):
    func: Expr
    args: Tuple[Expr] = a_field(factory=tuple)
    kwargs: Dict[str, Expr] = a_field(factory=dict)

    def __hash__(self):
        return hash(hash(self.func) + hash(self.args) + hash(frozendict(self.kwargs)))

@define
class Attr(Expr[T]):
    data: Expr
    attr_name: str  # static access so no ast involved

@define
class GetItem(Expr[T]):
    data: Expr
    key: Expr

@define
class Object(Expr[T]):
    """
    Use this to construct an AST and then compile it for any use.
    """
    data: Any  # holds user data

    def __hash__(self):
        return hash(id(self.data))

    # def __repr__(self):
    #     return f"Object({str(self.data)[:20]})".replace("\n", "").replace(" ", "")


def show_expr(expr: Expr[T], custom: Callable[[Expr[T]], Optional[str]] = lambda x: None) -> str:
    def _show_expr(expr):
        def eval_tuple(expr):
            return tuple(_show_expr(i) for i in expr)

        def eval_dict(expr):
            return {k: _show_expr(e) for k, e in expr.items()}

        reduced = custom(expr)
        if reduced:
            return reduced

        match expr:
            case Object(str() as x):
                return f'"{x}"'
            case Object(x):
                return str(x)
            case Call(f, args, kwargs):
                # hmm, this is complicated.
                func_str = _show_expr(f)
                args = list(eval_tuple(args))
                kwargs = eval_dict(kwargs)
                kwargs = [f"{k}={v}" for k, v in kwargs.items()]
                return f"{func_str}({','.join(args + kwargs)})"
            case Attr(data, str() as attr_name):
                return f"{_show_expr(data)}.{attr_name}"
            case GetItem(data, key):
                return f"{_show_expr(data)}[{_show_expr(key)}]"
            case DelegatedVar(wrapped, cxt):
                return f"{_show_expr(wrapped)}"
            case _:
                raise RuntimeError(f"unsupported ast found!:{expr}")

    return _show_expr(expr)


@dataclass
class AstProxyContextImpl(IProxyContext[Expr[T]]):
    eval_impl: Callable[[Expr[T]], T]
    iter_impl: Callable[[Expr[T]], Iterator[Expr[T]]] = field(default=None)
    _alias_name: str = field(default="AstProxy")

    def getattr(self, tgt: Expr[T], name: str):
        return self.pure(getattr(tgt, name))

    def call(self, tgt: Expr[T], *args, **kwargs):
        return self.pure(tgt(*args, **kwargs))

    def pure(self, tgt: Expr[T]) -> "DelegatedVar[T]":
        return DelegatedVar(tgt, self)

    def getitem(self, tgt: Expr[T], key) -> Any:
        return self.pure(tgt[key])

    def eval(self, tgt: Expr[T]):
        return self.eval_impl(tgt)

    def alias_name(self):
        return self._alias_name

    def iter(self, tgt: Expr[T]):
        if self.iter_impl is None:
            raise NotImplementedError("iter() not implemented for this context")
        return self.iter_impl(tgt)

    def dir(self,tgt:Expr[T]):
        return dir(tgt)

    def __str__(self):
        return f"{self._alias_name}Context"


def ast_proxy(tgt, cxt=AstProxyContextImpl(lambda x: x)):
    return DelegatedVar(Object(tgt), cxt)


class Applicative(Generic[T], ABC):
    @abstractmethod
    def map(self, target: T, f) -> T:
        pass

    @abstractmethod
    def zip(self, *targets: T):
        pass

    @abstractmethod
    def pure(self, item) -> T:
        pass

    @abstractmethod
    def is_instance(self, item)->bool:
        pass

    def dict(self, **kwargs: T) -> T:
        items = list(kwargs.items())
        keys = [t[0] for t in items]
        values = [t[1] for t in items]
        return self.zip(*values).map(lambda vs: dict(zip(keys, vs)))


def eval_app(expr: Expr[T], app: Applicative[T]) -> T:
    def _eval(expr):
        def eval_tuple(expr):
            return tuple(_eval(i) for i in expr)

        def eval_dict(expr):
            return valmap(_eval, expr)

        match expr:
            case DelegatedVar(Expr() as wrapped, AstProxyContextImpl()):
                return _eval(wrapped)
            case Object(x) if app.is_instance(x):
                return x
            case Object(x):
                return app.pure(x)
            case Call(Expr() as f, args, kwargs):
                injected_func: "T[Callable]" = _eval(f)
                args = app.zip(*eval_tuple(args))
                kwargs: "T[dict]" = app.dict(**eval_dict(kwargs))
                # now we are all in the world of injected. how can I combine them all?
                applied = app.map(app.zip(injected_func, args, kwargs),
                                  lambda t: t[0](*t[1], **t[2]))
                return applied
            case Attr(Expr() as data, str() as attr_name):
                injected_data: Injected = _eval(data)
                return app.map(
                    injected_data,
                    lambda x: getattr(x, attr_name)
                )

            case GetItem(Expr() as data, Expr() as key):
                injected_data: Injected = _eval(data)
                injected_key = _eval(key)
                return app.map(
                    app.zip(injected_data, injected_key),
                    lambda t: t[0][t[1]]
                )
            case _:
                raise RuntimeError(f"unsupported ast found!:{type(expr)},{expr}")

    return _eval(expr)


class ApplicativeInjectedImpl(Applicative[Injected]):

    def map(self, target: Injected, f) -> T:
        return target.map(f)

    def zip(self, *targets: Injected):
        return Injected.mzip(*targets)

    def pure(self, item) -> T:
        return Injected.pure(item)
    def is_instance(self, item) ->bool:
        return isinstance(item,Injected)


class ApplicativeDesignedImpl(Applicative[Designed]):

    def map(self, target: Designed, f) -> T:
        return target.map(f)

    def zip(self, *targets: Designed):
        return Designed.zip(*targets)

    def pure(self, item) -> T:
        return Designed.bind(Injected.pure(item))

    def is_instance(self, item) ->bool:
        return isinstance(item,Designed)


def reduce_injected_expr(expr: Expr):
    match expr:
        case Object(InjectedPure(value)):
            return str(value)
        case Object(Injected() as i):
            return f"{i.__class__.__name__}"


def reduce_designed_expr(expr: Expr):
    match expr:
        case Object(PureDesigned(design, InjectedPure(value))):
            return f"Object({str(value)} with {design})"


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


def eval_injected(expr: Expr[Injected]) -> EvaledInjected:
    return EvaledInjected(eval_app(expr, ApplicativeInjected), expr)


def eval_designed(expr: Expr[Designed]) -> Designed:
    return EvaledDesigned(eval_app(expr, ApplicativeDesigned), expr)


def injected_proxy(injected: Injected) -> DelegatedVar[Injected]:
    return ast_proxy(injected, InjectedEvalContext)


def designed_proxy(designed: Designed) -> DelegatedVar[Designed]:
    return ast_proxy(designed, DesignedEvalContext)


ApplicativeInjected = ApplicativeInjectedImpl()
ApplicativeDesigned = ApplicativeDesignedImpl()
InjectedEvalContext = AstProxyContextImpl(eval_injected, _alias_name="InjectedProxy")
DesignedEvalContext = AstProxyContextImpl(eval_designed, _alias_name="DesignedProxy")
