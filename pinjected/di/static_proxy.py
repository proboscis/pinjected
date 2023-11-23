from dataclasses import dataclass, field
from typing import Any, Callable, Iterator

from cytoolz import valmap

from pinjected.di.applicative import Applicative
from pinjected.di.ast import Expr, Call, Attr, GetItem, Object, BiOp
from pinjected.di.proxiable import T, DelegatedVar, IProxyContext


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

    def dir(self, tgt: Expr[T]):
        return dir(tgt)

    def __str__(self):
        return f"{self._alias_name}Context"

    def __hash__(self):
        return hash(self._alias_name)

    def biop_impl(self, op: str, tgt: Expr[T], other):
        match op:
            case '+':
                return self.pure(tgt + other)
            case '-':
                return self.pure(tgt - other)
            case '*':
                return self.pure(tgt * other)
            case '/':
                return self.pure(tgt / other)
            case '%':
                return self.pure(tgt % other)
            case '**':
                return self.pure(tgt ** other)
            case '<<':
                return self.pure(tgt << other)
            case '>>':
                return self.pure(tgt >> other)
            case '&':
                return self.pure(tgt & other)
            case '^':
                return self.pure(tgt ^ other)
            case '|':
                return self.pure(tgt | other)
            case '//':
                return self.pure(tgt // other)
            case '@':
                return self.pure(tgt @ other)
            case '==':
                return self.pure(tgt == other)
            case _:
                raise NotImplementedError(f"biop {op} not implemented")


def ast_proxy(tgt, cxt=AstProxyContextImpl(lambda x: x)):
    return DelegatedVar(Object(tgt), cxt)


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
                return app.map(t, list)
            case Object(([*items] as x)) if isinstance(x, tuple):
                t = app.zip(*[ensure_pure(item) for item in items])
                return app.map(t, tuple)
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
            # case BiOp('+', Expr() as left, Expr() as right):
            #     injected_left = _eval(left)
            #     injected_right = _eval(right)
            #     return app.map(
            #         app.zip(injected_left, injected_right),
            #         lambda t: t[0] + t[1]
            #     )
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
            case _:
                raise RuntimeError(f"unsupported ast found!:{type(expr)},{expr}")

    try:
        return _eval(expr)
    except AttributeError as e:
        raise RuntimeError(f"failed to evaluate {expr}") from e
