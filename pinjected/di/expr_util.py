from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Generic, Tuple, Dict, Any, Callable, Optional, TypeVar

from frozendict import frozendict

from pinjected.di.injected_analysis import get_instance_origin
from pinjected.global_configs import pinjected_TRACK_ORIGIN

T = TypeVar("T")

ASSERT_PICKLABLE = False


def assert_picklable(target, name):
    import cloudpickle
    if not ASSERT_PICKLABLE:
        return
    try:
        cloudpickle.dumps(target)
    except Exception as e:
        raise RuntimeError(f"target {name} is not picklable.\ntype={type(target)}\nvalue={target}") from e


class Expr(Generic[T], ABC):
    """
    I want to know where this instance is instantiated
    """

    def __post_init__(self):
        # this takes time so... we need to toggle it
        if pinjected_TRACK_ORIGIN:
            self.origin_frame = get_instance_origin('pinjected')
        else:
            self.origin_frame = None

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

    # def __str__(self):
    #     return f"Expr(>{show_expr(self)}<)"
    #
    # def __repr__(self):
    #     return str(self)

    def biop(self, op, other):
        match op:
            case '+':
                return BiOp("+", self, self._wrap_if_non_expr(other))
            case '|':
                return BiOp("|", self, self._wrap_if_non_expr(other))
            case '&':
                return BiOp("&", self, self._wrap_if_non_expr(other))
            case '-':
                return BiOp("-", self, self._wrap_if_non_expr(other))
            case '*':
                return BiOp("*", self, self._wrap_if_non_expr(other))
            case '@':
                return BiOp("@", self, self._wrap_if_non_expr(other))
            case '/':
                return BiOp("/", self, self._wrap_if_non_expr(other))
            case '//':
                return BiOp("//", self, self._wrap_if_non_expr(other))
            case '%':
                return BiOp("%", self, self._wrap_if_non_expr(other))
            case '**':
                return BiOp("**", self, self._wrap_if_non_expr(other))
            case '<<':
                return BiOp("<<", self, self._wrap_if_non_expr(other))
            case '>>':
                return BiOp(">>", self, self._wrap_if_non_expr(other))
            case '^':
                return BiOp("^", self, self._wrap_if_non_expr(other))
            case '==':
                return BiOp("==", self, self._wrap_if_non_expr(other))
            case _:
                raise NotImplementedError(f"biop {op} not implemented")
    def unary(self, op):
        match op:
            case '-':
                return UnaryOp("-", self)
            case '~':
                return UnaryOp("~", self)
            case 'not':
                return UnaryOp("not", self)
            case 'await':
                return UnaryOp("await", self)
            case _:
                raise NotImplementedError(f"unary {op} not implemented")

    def _await_(self):
        return UnaryOp("await", self)


@dataclass
class BiOp(Expr):
    name: str
    left: Expr
    right: Expr

    def __post_init__(self):
        super().__post_init__()
        assert isinstance(self.left, Expr), f"{self.left} is not an Expr"
        assert isinstance(self.right, Expr), f"{self.right} is not an Expr"
        assert isinstance(self.name, str), f"{self.name} is not a str"
        assert_picklable(self.left, "left")
        assert_picklable(self.right, "right")

    def __getstate__(self):
        return self.name, self.left, self.right, self.origin_frame

    def __setstate__(self, state):
        self.name, self.left, self.right, self.origin_frame = state

    def __hash__(self):
        return hash((self.name, self.left, self.right))


@dataclass
class UnaryOp(Expr):
    name: str
    target: Expr

    def __post_init__(self):
        super().__post_init__()
        assert isinstance(self.target, Expr), f"{self.target} is not an Expr"
        assert isinstance(self.name, str), f"{self.name} is not a str"
        assert_picklable(self.target, "target")

    def __getstate__(self):
        return self.name, self.target, self.origin_frame

    def __setstate__(self, state):
        self.name, self.target, self.origin_frame = state

    def __hash__(self):
        return hash((self.name, self.target))


@dataclass
class Call(Expr):
    func: Expr
    args: Tuple[Expr] = field(default_factory=tuple)
    kwargs: Dict[str, Expr] = field(default_factory=dict)

    def __post_init__(self):
        super().__post_init__()
        assert_picklable(self.func, "func")
        for i, arg in enumerate(self.args):
            assert_picklable(arg, f"args[{i}]")
        for k, v in self.kwargs.items():
            assert_picklable(v, f"kwargs[{k}]")

    def __getstate__(self):
        return self.func, self.args, self.kwargs, self.origin_frame

    def __setstate__(self, state):
        self.func, self.args, self.kwargs, self.origin_frame = state

    def __hash__(self):
        return hash((self.func, self.args, frozendict(self.kwargs)))


@dataclass
class Attr(Expr):
    data: Expr
    attr_name: str  # static access so no ast involved

    def __post_init__(self):
        super().__post_init__()
        assert isinstance(self.data, Expr), f"{self.data} is not an Expr"
        assert isinstance(self.attr_name, str), f"{self.attr_name} is not a str"
        assert_picklable(self.data, "data")

    def __getstate__(self):
        return self.data, self.attr_name, self.origin_frame

    def __setstate__(self, state):
        self.data, self.attr_name, self.origin_frame = state

    def __hash__(self):
        return hash((self.data, self.attr_name))


@dataclass
class GetItem(Expr):
    data: Expr
    key: Expr

    def __post_init__(self):
        super().__post_init__()
        assert isinstance(self.data, Expr), f"{self.data} is not an Expr"
        assert isinstance(self.key, Expr), f"{self.key} is not an Expr"
        assert_picklable(self.data, "data")
        assert_picklable(self.key, "key")

    def __getstate__(self):
        return self.data, self.key, self.origin_frame

    def __setstate__(self, state):
        self.data, self.key, self.origin_frame = state

    def __hash__(self):
        return hash((self.data, self.key))


@dataclass
class Object(Expr):
    """
    Use this to construct an AST and then compile it for any use.
    """
    data: Any  # holds user data

    def __post_init__(self):
        super().__post_init__()
        assert_picklable(self.data, 'data')

    def __getstate__(self):
        return self.data, self.origin_frame

    def __setstate__(self, state):
        self.data, self.origin_frame = state

    def __hash__(self):
        # what if the data is not hashable?
        try:
            # here we include type of hash since hash(1) == hash(True)
            # we also add type_hash since hash(0) == 0 == hash(False)
            type_hash = hash(type(self.data))
            return hash(self.data) * type_hash + type_hash
        except TypeError as e:
            return hash(id(self.data))


@dataclass
class Cache(Expr):
    src: Expr

    def __post_init__(self):
        super().__post_init__()
        assert isinstance(self.src, Expr), f"{self.src} is not an Expr"

    def __getstate__(self):
        return self.src

    def __setstate__(self, state):
        self.src = state

    def __hash__(self):
        return hash(f"cached") + hash(self.src)


def show_expr(expr: Expr[T], custom: Callable[[Expr[T]], Optional[str]] = lambda x: None) -> str:
    from pinjected.di.proxiable import DelegatedVar
    def eval_tuple(e):
        res = tuple(_show_expr(i) for i in e)
        flag = all(isinstance(i, str) for i in res)
        if not flag:
            raise RuntimeError(f"unsupported ast found!:{type(e)}")
        return res

    def eval_dict(e):
        return {k: _show_expr(e) for k, e in e.items()}

    def _show_expr(e: Expr):

        reduced = custom(e)
        if reduced:
            from loguru import logger
            logger.info(f"reduced:{reduced}")
            return reduced
        match e:
            case Object(DelegatedVar(wrapped, cxt) as dv):
                return _show_expr(dv)
            case Object(x) if hasattr(x, "__repr_expr__"):
                res = x.__repr_expr__()
                assert isinstance(res, str), f"{res} is not a str, v is {type(x)}"
                return res
            case Object(str() as x):
                return f'"{x}"'
            case Object(x):
                return f"{str(x)}"
            case Call(f, args, kwargs):
                # hmm, this is complicated.
                func_str = _show_expr(f)
                args = list(eval_tuple(args))
                kwargs = eval_dict(kwargs)
                kwargs = [f"{k}={v}" for k, v in kwargs.items()]
                return f"{func_str}({','.join(args + kwargs)})"
            case BiOp(str() as op, Expr() as left, Expr() as right):
                return f"({_show_expr(left)} {op} {_show_expr(right)})"
            case Attr(Expr() as data, str() as attr_name):
                return f"{_show_expr(data)}.{attr_name}"
            case GetItem(Expr() as data, key):
                return f"{_show_expr(data)}[{_show_expr(key)}]"
            case DelegatedVar(wrapped, cxt):
                return f"{_show_expr(wrapped)}"
            case UnaryOp('await', Expr() as tgt):
                return f"(await {_show_expr(tgt)})"
            case UnaryOp(op, Expr() as tgt):
                return f"{op}({_show_expr(tgt)})"
            case Cache(Expr() as tgt):
                return f"{_show_expr(tgt)}"
            case _:
                raise RuntimeError(f"unsupported ast found!:{type(e)}")

    return _show_expr(expr)
