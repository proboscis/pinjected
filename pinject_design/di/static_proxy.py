from dataclasses import dataclass, field
from typing import Any, Callable, Iterator

from cytoolz import valmap

from pinject_design.di.applicative import Applicative
from pinject_design.di.ast import Expr, Call, Attr, GetItem, Object
from pinject_design.di.proxiable import T, DelegatedVar, IProxyContext


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


def ast_proxy(tgt, cxt=AstProxyContextImpl(lambda x: x)):
    return DelegatedVar(Object(tgt), cxt)


def eval_app(expr: Expr[T], app: Applicative[T]) -> T:
    def _eval(expr):
        def eval_tuple(expr):
            return tuple(_eval(i) for i in expr)

        def eval_dict(expr):
            return valmap(_eval, expr)

        match expr:
            case Object(DelegatedVar(Expr() as wrapped, AstProxyContextImpl())):
                return _eval(wrapped)
            case Object(x) if app.is_instance(x):
                return x
            #case Object(DelegatedVar() as var):
            #    return var.eval()
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
                injected_data = _eval(data)
                return app.map(
                    injected_data,
                    lambda x: getattr(x, attr_name)
                )

            case GetItem(Expr() as data, Expr() as key):
                injected_data = _eval(data)
                injected_key = _eval(key)
                return app.map(
                    app.zip(injected_data, injected_key),
                    lambda t: t[0][t[1]]
                )
            case _:
                raise RuntimeError(f"unsupported ast found!:{type(expr)},{expr}")

    return _eval(expr)
