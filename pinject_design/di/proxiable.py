from abc import abstractmethod, ABC
from dataclasses import dataclass, field
from typing import Generic, TypeVar, Any, Callable, Tuple, Dict, Set, Optional

from cytoolz import valmap
from frozendict import frozendict

from pinject_design import Injected, Designed, Design
from pinject_design.di.designed import PureDesigned
from pinject_design.di.injected import InjectedPure

T = TypeVar("T")


class IProxyContext(Generic[T]):

    @abstractmethod
    def getattr(self, tgt: T, name: str):
        pass

    @abstractmethod
    def call(self, tgt: T, *args, **kwargs):
        pass

    @abstractmethod
    def pure(self, tgt: T) -> "DelegatedVar[T]":
        pass

    @abstractmethod
    def getitem(self, tgt: T, key) -> Any:
        pass

    @abstractmethod
    def eval(self, tgt: T):
        pass

    @abstractmethod
    def alias_name(self):
        pass


@dataclass
class DelegatedVar(Generic[T]):  # Generic Var Type that delegates all implementations to cxt.
    _value: T
    _cxt: IProxyContext[T]

    def __getattr__(self, item):
        return self._cxt.getattr(self._value, item)

    def __call__(self, *args, **kwargs):
        return self._cxt.call(self._value, *args, **kwargs)

    def __getitem__(self, key):
        return self._cxt.getitem(self._value, key)

    def eval(self):
        """invoke resolution on the value"""
        return self._cxt.eval(self._value)

    def __str__(self):
        return f"{self._cxt.alias_name()}({self._value},{self._cxt})"


class Expr(Generic[T]):
    def __getattr__(self, item: str):
        return Attr(self, item)

    def __call__(self, *args: "Expr", **kwargs: "Expr"):
        return Call(self, args, kwargs)

    def __getitem__(self, item: "Expr"):
        return GetItem(self, item)

    def __str__(self):
        return f"Expr({show_expr(self)})"

    def __repr__(self):
        return str(self)


@dataclass(frozen=True)
class Call(Expr[T]):
    func: Expr
    args: Tuple[Expr] = field(default_factory=tuple)
    kwargs: Dict[str, Expr] = field(default_factory=dict)

    def __hash__(self):
        return hash(hash(self.func) + hash(self.args) + hash(frozendict(self.kwargs)))


@dataclass(frozen=True)
class Attr(Expr[T]):
    data: Expr
    attr_name: str  # static access so no ast involved


@dataclass(frozen=True)
class GetItem(Expr[T]):
    data: Expr
    key: Expr


@dataclass(frozen=True)
class Object(Expr[T]):
    """
    Use this to construct an AST and then compile it for any use.
    """
    data: Any  # holds user data

    def __hash__(self):
        return hash(id(self.data))

    def __repr__(self):
        return f"Object({str(self.data)[:20]})".replace("\n", "").replace(" ", "")


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
    # upon calling iter() and next(), I think we need to call eval()
    # and yield the delegated vars this means the delegated var supports iterator


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
            case Object(x):
                return app.pure(x)
            case Call(f, args, kwargs):
                injected_func: "T[Callable]" = _eval(f)
                args = app.zip(*eval_tuple(args))
                kwargs: "T[dict]" = app.dict(**eval_dict(kwargs))
                # now we are all in the world of injected. how can I combine them all?
                applied = app.map(app.zip(injected_func, args, kwargs),
                                  lambda _f, _args, _kwargs: _f(*_args, **_kwargs))
                return applied
            case Attr(data, str() as attr_name):
                injected_data: Injected = _eval(data)
                return app.map(
                    injected_data,
                    lambda x: getattr(x, attr_name)
                )

            case GetItem(data, key):
                injected_data: Injected = _eval(data)
                injected_key = _eval(key)
                return app.map(
                    app.zip(injected_data, injected_key),
                    lambda _data, _key: _data[_key]
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


ApplicativeInjected = ApplicativeInjectedImpl()


class ApplicativeDesignedImpl(Applicative[Designed]):

    def map(self, target: Designed, f) -> T:
        return target.map(f)

    def zip(self, *targets: Designed):
        return Designed.zip(*targets)

    def pure(self, item) -> T:
        return Designed.bind(Injected.pure(item))


ApplicativeDesigned = ApplicativeDesignedImpl()


def reduce_injected_expr(expr: Expr):
    match expr:
        case Object(InjectedPure(value)):
            return str(value)
        case Object(Injected() as i):
            return f"{i.__class__.__name__}"

def reduce_designed_expr(expr:Expr):
    match expr:
        case Object(PureDesigned(design,InjectedPure(value))):
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
    return EvaledDesigned(eval_app(expr, ApplicativeDesigned),expr)


InjectedEvalContext = AstProxyContextImpl(eval_injected, "InjectedProxy")
DesignedEvalContext = AstProxyContextImpl(eval_designed, "DesignedProxy")


def injected_proxy(injected: Injected) -> DelegatedVar[Injected]:
    return ast_proxy(injected, InjectedEvalContext)


def designed_proxy(designed: Designed) -> DelegatedVar[Designed]:
    return ast_proxy(designed, DesignedEvalContext)
