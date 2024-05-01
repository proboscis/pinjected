import asyncio
import inspect
import operator
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Union, Callable, Dict, Any, Optional

from loguru import logger

from pinjected import Injected
from pinjected.di.app_injected import await_awaitables, walk_replace, EvaledInjected
from pinjected.di.ast import Expr, Object, Call, BiOp, UnaryOp, Attr, GetItem
from pinjected.di.injected import extract_dependency
from pinjected.di.proxiable import DelegatedVar
from pinjected.v2.binds import IBind, BindInjected
from pinjected.v2.keys import IBindKey, StrBindKey, DestructorKey
from pinjected.v2.provide_context import ProvideContext

Providable = Union[str, IBindKey, Callable, IBind]


class IScope(ABC):
    @abstractmethod
    def provide(self, tgt: IBindKey, cxt: ProvideContext, provider: Callable[[IBindKey, ProvideContext], Any]):
        pass


class ScopeNode(IScope):
    objects: Dict[IBindKey, Any] = field(default_factory=dict)

    def provide(self, tgt: IBindKey, cxt: ProvideContext, provider: Callable[[IBindKey, ProvideContext], Any]):
        if tgt not in self.objects:
            self.objects[tgt] = provider(tgt, cxt)

        return self.objects[tgt]


# We need a lock for each Bind Key.

@dataclass
class AsyncLockMap:
    locks: Dict[IBindKey, asyncio.Lock] = field(default_factory=dict)

    def get(self, key: IBindKey):
        if key not in self.locks:
            self.locks[key] = asyncio.Lock()
        return self.locks[key]


OPERATORS = {
    '+': operator.add,
    '-': operator.sub,
    '*': operator.mul,
    '/': operator.truediv,
    '//': operator.floordiv,
    '%': operator.mod,
    '**': operator.pow,
    '==': operator.eq,
    '!=': operator.ne,
    '>': operator.gt,
    '<': operator.lt,
    '>=': operator.ge,
    '<=': operator.le,
    '<<': operator.lshift,
    '>>': operator.rshift,
    '&': operator.and_,
    '|': operator.or_,
    '^': operator.xor
}
UNARY_OPS = {
    '+': operator.pos,
    '-': operator.neg,
    '~': operator.invert,
    'not': operator.not_
}


@dataclass
class Cache(Expr):
    src: Expr

    def __getstate__(self):
        return self.src

    def __setstate__(self, state):
        self.src = state

    def __hash__(self):
        return hash(f"cached") + hash(self.src)


@dataclass
class AsyncResolver:
    design: "Design"
    parent: Optional["AsyncResolver"] = None
    objects: Dict[IBindKey, Any] = field(default_factory=dict)
    locks: AsyncLockMap = field(default_factory=AsyncLockMap)

    def __post_init__(self):
        from pinjected import injected, instance, providers
        async def dummy():
            raise RuntimeError('This should never be instantiated')

        dummy = Injected.bind(dummy)

        self.design = self.design + providers(
            __resolver__=dummy,
            __design__=dummy
        )
        self.objects = {
            StrBindKey("__resolver__"): self,
            StrBindKey("__design__"): self.design
        }
        self.eval_memos = {}
        self.eval_locks = defaultdict(asyncio.Lock)
        self.destruction_lock = asyncio.Lock()
        self.destructed = False

    async def _optimize(self, expr: Expr):
        """
        this finds duplicated expr in the node and replace it with Cache Node.
        """
        return walk_replace(expr, lambda x: Cache(x))

    async def eval_expr(self, expr: Expr):
        assert isinstance(expr, Expr), f"expr must be Expr, got {expr} of type {type(expr)}"
        match expr:
            case Cache(src):
                k = hash(src)
                async with self.eval_locks[k]:
                    if k in self.eval_memos:
                        res = self.eval_memos[k]
                    else:
                        res = await self.eval_expr(src)
                        self.eval_memos[k] = res

            case Object(DelegatedVar(value, cxt)):
                res = await self.eval_expr(value)
            case Object(Injected() as _injected):
                res = await self._provide_providable(_injected)
            case Object(x):
                res = x
            case Call(f, args, kwargs):
                args = asyncio.gather(*[self.eval_expr(a) for a in args])
                keys = list(kwargs.keys())
                values = asyncio.gather(*[self.eval_expr(v) for v in kwargs.values()])
                f, args, values = await asyncio.gather(self.eval_expr(f), args, values)
                kwargs = dict(zip(keys, values))
                res = f(*args, **kwargs)
            case BiOp(op, left, right):
                left, right = await asyncio.gather(self.eval_expr(left), self.eval_expr(right))
                res = OPERATORS[op](left, right)
            case UnaryOp('await', data):
                data = await self.eval_expr(data)
                res = await data
            case UnaryOp(name, data):
                data = await self.eval_expr(data)
                res = UNARY_OPS[name](data)
            case Attr(data, name):
                data = await self.eval_expr(data)
                res = getattr(data, name)
            case GetItem(data, key):
                data, key = await asyncio.gather(self.eval_expr(data), self.eval_expr(key))
                res = data[key]
            case _:
                raise TypeError(
                    f"expr must be Object, Call, BiOp, UnaryOp, Attr or GetItem, got {expr} of type {type(expr)}")
        return res

    async def _provide(self, key: IBindKey, cxt: ProvideContext):
        # we need to think which one to ask provider
        # if we have the binding for the key, use our own scope
        async with self.locks.get(key):
            if key in self.objects:
                data = self.objects[key]
                return data
            elif key in self.design:
                logger.info(f"{cxt.trace_str}")
                # we are responsible for providing this
                bind = self.design.bindings[key]
                dep_keys = list(bind.dependencies)
                tasks = []
                for dep_key in dep_keys:
                    n_cxt = ProvideContext(self, key=dep_key, parent=cxt)
                    tasks.append(self._provide(dep_key, n_cxt))
                res = await asyncio.gather(*tasks)
                deps = dict(zip(dep_keys, res))
                data = await bind.provide(cxt, deps)
                self.objects[key] = data
                show_data = str(data)[:100]
                logger.info(f"{cxt.trace_str} := {show_data}")
                return data
            else:
                if self.parent is not None:
                    return await self.parent._provide(key, cxt)
                else:
                    raise KeyError(f"Key {key} not found in design in {cxt.trace_str}")

    def child_session(self, overrides: "Design"):
        return AsyncResolver(overrides, parent=self)

    async def _provide_providable(self, tgt: Providable):
        async def resolve_deps(keys: set[IBindKey]):
            tasks = [self._provide(k, ProvideContext(self, key=k, parent=None)) for k in keys]
            return {k: v for k, v in zip(keys, await asyncio.gather(*tasks))}

        match tgt:
            case str():
                return await self._provide(StrBindKey(tgt), ProvideContext(self, key=StrBindKey(tgt), parent=None))
            case IBindKey():
                return await self._provide(tgt, ProvideContext(self, key=tgt, parent=None))
            case DelegatedVar(value, cxt) as dv:
                # return await self._provide_providable(tgt.eval())
                expr = await self._optimize(dv.eval().ast)
                return await self.eval_expr(expr)
            case EvaledInjected(val, ast):
                expr = await self._optimize(ast)
                return await self.eval_expr(expr)
            case Injected() as i_tgt:
                return await self._provide_providable(BindInjected(i_tgt))
            case IBind():
                deps = await resolve_deps(tgt.dependencies)
                return await tgt.provide(ProvideContext(self, key=tgt, parent=None), deps)
            case func if inspect.isfunction:
                deps = extract_dependency(func)
                logger.info(f"Resolving deps for {func} -> {deps}")
                keys = {StrBindKey(d) for d in deps}
                deps = await resolve_deps(keys)
                kwargs = {k.name: v for k, v in deps.items()}
                data = tgt(**kwargs)
                if inspect.iscoroutinefunction(tgt):
                    return await data
                else:
                    return data
            case _:
                raise TypeError(f"tgt must be str, IBindKey, Callable or IBind, got {tgt}")

    async def provide(self, tgt: Providable):
        logger.info(f"providing {tgt}")
        return await self._provide_providable(tgt)

    def to_blocking(self):
        return Resolver(self)

    def __getitem__(self, item):
        return self.provide(item)

    async def destruct(self):
        """
        check objects and destruct them if they are destructable.
        """

        def a_destructor(f):
            async def impl(tgt):
                return f(tgt)

            return impl

        async with self.destruction_lock:
            assert not self.destructed, "Resolver already destructed"
            destructions = []
            for k, v in list(self.objects.items()):
                destruction_key = DestructorKey(k)
                if destruction_key in self.design:
                    destructor = await self[destruction_key]
                    if not inspect.iscoroutinefunction(destructor):
                        destructor = a_destructor(destructor)
                    destructions.append(destructor(v))
            logger.info(f"waiting for {len(destructions)} destructors to finish.")
            results = await asyncio.gather(*destructions)
            logger.success(f"all destructors finished with results:{results}")
            self.destructed = True
            logger.success(f"Resolver destructed")
            return results


@dataclass
class Resolver:
    resolver: AsyncResolver

    def provide(self, tgt: Providable):
        return asyncio.run(self.resolver.provide(tgt))

    def child_session(self, overrides: "Design"):
        return Resolver(self.resolver.child_session(overrides))

    def to_async(self):
        return self.resolver

    def __getitem__(self, item):
        return self.provide(item)
