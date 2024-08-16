from dataclasses import dataclass, field
from typing import Any, Callable, Iterator

from cytoolz import valmap

from pinjected.di.applicative import Applicative
from pinjected.di.expr_util import Expr, Call, Attr, GetItem, Object, BiOp, UnaryOp
from pinjected.di.func_util import fix_args_kwargs
from pinjected.di.proxiable import T, DelegatedVar, IProxyContext


@dataclass
class AstProxyContextImpl(IProxyContext[Expr[T]]):
    eval_impl: Callable[[Expr[T]], T]
    iter_impl: Callable[[Expr[T]], Iterator[Expr[T]]] = field(default=None)
    _alias_name: str = field(default="AstProxy")

    def getattr(self, tgt: Expr[T], name: str):
        return self.pure(getattr(tgt, name))

    def call(self, ___pinjected_tgt___: Expr[T], *args, **kwargs):
        return self.pure(___pinjected_tgt___(*args, **kwargs))

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

    def dir(self, tgt: Expr[T]):
        return dir(tgt)

    def __str__(self):
        return f"{self._alias_name}Context"

    def __hash__(self):
        return hash(self._alias_name)

    def biop_impl(self, op: str, tgt: Expr[T], other):
        return self.pure(tgt.biop(op, other))

    def unary_impl(self, op: str, tgt: Expr[T]):
        match op:
            case 'await':
                return self.pure(tgt._await_())
            case _:
                raise NotImplementedError(f"unary {op} not implemented")


def ast_proxy(tgt, cxt=AstProxyContextImpl(lambda x: x)):
    return DelegatedVar(tgt, cxt)


def en_list(thing):
    return list(thing)


def en_tuple(thing):
    return tuple(thing)


def eval_applicative(expr: Expr[T], app: Applicative[T]) -> T:
    def _eval(expr):
        def eval_tuple(expr):
            return tuple(_eval(i) for i in expr)

        def eval_dict(expr):
            return valmap(_eval, expr)

        def ensure_pure(item):
            match item:
                case item if app.is_instance(item):
                    return item
                case DelegatedVar(Expr() as wrapped, AstProxyContextImpl()):
                    return _eval(wrapped)
                case item:
                    return app.pure(item)

        match expr:
            case Object([*items] as x) if isinstance(x, list):
                t = app.zip(*[ensure_pure(item) for item in items])
                return app.map(t, en_list)
            case Object(([*items] as x)) if isinstance(x, tuple):
                t = app.zip(*[ensure_pure(item) for item in items])
                return app.map(t, en_tuple)
            case Object({**items} as x) if isinstance(x, dict):
                values = app.zip(*[ensure_pure(item) for item in items.values()])
                return app.map(values, lambda t: {k: v for k, v in zip(items.keys(), t)})

            case Object(x):
                return ensure_pure(x)
            case Call(Expr() as f, args, kwargs):
                injected_func: "T[Callable]" = _eval(f)
                args = app.zip(*eval_tuple(args))
                kwargs: "T[dict]" = app.dict(**eval_dict(kwargs))

                # now we are all in the world of injected. how can I combine them all?
                # so all the arguments are converted into Injected if not, then combined together
                # so if you are to pass an Injected as an argument, you must wrap it with Injected.pure
                def apply(t):
                    from loguru import logger
                    func, args, kwargs = t
                    # args,kwargs = fix_args_kwargs(func,args,kwargs)
                    return func(*args, **kwargs)

                applied = app.map(app.zip(injected_func, args, kwargs), apply)
                return applied
            case Attr(Expr() as data, str() as attr_name):
                injected_data = _eval(data)

                def try_get_attr(x):
                    try:
                        return getattr(x, attr_name)
                    except AttributeError as e:
                        raise RuntimeError(f"failed to get attribute {attr_name} from {x} in AST:{data}") from e

                return app.map(
                    injected_data,
                    try_get_attr
                )

            case GetItem(Expr() as data, Expr() as key):
                injected_data = _eval(data)
                injected_key = _eval(key)
                return app.map(
                    app.zip(injected_data, injected_key),
                    lambda t: t[0][t[1]]
                )
            case BiOp(op, Expr() as left, Expr() as right):
                injected_left = _eval(left)
                injected_right = _eval(right)

                def eval_biop(t):
                    x, y = t
                    return eval("x " + op + " y", None, dict(x=x, y=y))

                return app.map(
                    app.zip(injected_left, injected_right),
                    eval_biop
                )
            case UnaryOp('await', Expr() as tgt):
                injected_tgt = _eval(tgt)
                return app._await_(injected_tgt)
            case _:
                raise RuntimeError(f"unsupported ast found!:{type(expr)},{expr}")

    try:
        return _eval(expr)
    except AttributeError as e:
        raise RuntimeError(f"failed to evaluate {expr}") from e
