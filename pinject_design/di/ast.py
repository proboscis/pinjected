from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Generic, Tuple, Dict, Any, Callable, Optional, TypeVar

from frozendict import frozendict

T = TypeVar("T")


class Expr(Generic[T], ABC):
    def __getattr__(self, item: str):
        return Attr(self, item)

    def _wrap_if_non_expr(self, item) -> "Expr":
        if not isinstance(item, Expr):
            return Object(item)
        else:
            return item

    def __call__(self, *args: "Expr", **kwargs: "Expr"):
        # print(f"{self}->args:{args},kwargs:{kwargs}")
        return Call(self,
                    tuple([self._wrap_if_non_expr(item) for item in args]),
                    {k: self._wrap_if_non_expr(v) for k, v in kwargs.items()}
                    )

    def __getitem__(self, item: "Expr"):
        return GetItem(self, self._wrap_if_non_expr(item))

    @abstractmethod
    def __getstate__(self):
        pass

    @abstractmethod
    def __setstate__(self, state):
        pass

    def __str__(self):
        return f"Expr(>{show_expr(self)}<)"

    def __repr__(self):
        return str(self)


@dataclass
class Call(Expr):
    func: Expr
    args: Tuple[Expr] = field(default_factory=tuple)
    kwargs: Dict[str, Expr] = field(default_factory=dict)

    def __getstate__(self):
        return self.func, self.args, self.kwargs

    def __setstate__(self, state):
        self.func, self.args, self.kwargs = state


@dataclass
class Attr(Expr):
    data: Expr
    attr_name: str  # static access so no ast involved

    def __getstate__(self):
        return self.data, self.attr_name

    def __setstate__(self, state):
        self.data, self.attr_name = state


@dataclass
class GetItem(Expr):
    data: Expr
    key: Expr

    def __getstate__(self):
        return self.data, self.key

    def __setstate__(self, state):
        self.data, self.key = state


@dataclass
class Object(Expr):
    """
    Use this to construct an AST and then compile it for any use.
    """
    data: Any  # holds user data

    def __getstate__(self):
        return self.data

    def __setstate__(self, state):
        self.data = state


def show_expr(expr: Expr[T], custom: Callable[[Expr[T]], Optional[str]] = lambda x: None) -> str:
    from pinject_design.di.proxiable import DelegatedVar
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
