
from loguru import logger

from pinjected.compatibility.task_group import TaskGroup
from pinjected.di.design_interface import ProvisionValidator
from pinjected.di.implicit_globals import IMPLICIT_BINDINGS
from pinjected.di.validation import ValFailure, ValSuccess
from pinjected.v2.callback import IResolverCallback
from pinjected.v2.events import ResolverEvent, RequestEvent, ProvideEvent, DepsReadyEvent, EvalRequestEvent, \
    CallInEvalStart, CallInEvalEnd, EvalResultEvent

try:
    import nest_asyncio
    import uvloop

    logger.error(
        f"nest_asyncio is disabled since uvloop is also installed! nest_asyncio.apply do not work with uvloop!")
    nest_asyncio.apply = lambda: None
except ImportError:
    pass

import asyncio
import datetime
import inspect
import operator
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from pprint import pformat
from typing import Union, Callable, Dict, Any, Optional

from loguru import logger

from pinjected import Injected
from pinjected.di.app_injected import walk_replace, EvaledInjected
from pinjected.di.expr_util import Expr, Object, Call, BiOp, UnaryOp, Attr, GetItem, show_expr, Cache
from pinjected.di.injected import extract_dependency
from pinjected.di.proxiable import DelegatedVar
from pinjected.exceptions import DependencyResolutionError, DependencyValidationError
from pinjected.v2.binds import IBind, BindInjected
from pinjected.v2.keys import IBindKey, StrBindKey, DestructorKey
from pinjected.v2.provide_context import ProvideContext
from pinjected.visualize_di import DIGraph

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


class EvaluationError(Exception):
    def __init__(self, cxt: ProvideContext, cxt_expr: Expr, cause_expr: Expr, src):
        self.cxt = cxt
        self.cxt_expr = cxt_expr
        self.cause_expr = cause_expr
        self.src = src
        super().__init__(f"""
EvaluationError:
    Context: {cxt.trace_str}
    Context Expr: {show_expr(cxt_expr)}
    Cause Expr: {show_expr(cause_expr)}
    Source: {src}
        """)


@dataclass
class AsyncResolver:
    design: "Design"
    parent: Optional["AsyncResolver"] = None
    objects: Dict[IBindKey, Any] = field(default_factory=dict)
    locks: AsyncLockMap = field(default_factory=AsyncLockMap)
    callbacks: list[IResolverCallback] = field(default=None)
    """
    if parent exists, we need to check if the injection targets
    needs to be re-created due overrides, or not.
    
    """

    def add_callback(self, callback: IResolverCallback):
        self.callbacks.append(callback)

    def _callback(self, event: ResolverEvent):
        for cb in self.callbacks:
            cb(event)

    def __post_init__(self):
        from pinjected import Design
        if self.callbacks is None:
            self.callbacks = [
                # BaseResolverCallback()
            ]
        assert self.callbacks is not None
        self.design = Design.from_bindings(IMPLICIT_BINDINGS) + self.design

        from pinjected import providers
        async def dummy():
            raise RuntimeError('This should never be instantiated')

        dummy = Injected.bind(dummy)

        # maybe,,, we can obtain __pinjected_provision_callback__ from design.
        # but provision involves instantiating this resolver, resulting in recursion.
        # The solution is to introduce a 'phase' for provision
        # 1. preparation phase, instantiate all stuff like __pinjected_....__.
        # 2. user provision phase, where user can provide stuff. we use __pinjected_...__ to provide stuff.
        # I think we should stick to constructor injection for simplicity.

        self.design = self.design + providers(
            __resolver__=dummy,
            __design__=dummy,
            __task_group__=dummy,
        )
        self.objects = {
            StrBindKey("__resolver__"): self,
            StrBindKey("__design__"): self.design,
        }
        self.eval_memos = {}
        self.eval_locks = defaultdict(asyncio.Lock)
        self.destruction_lock = asyncio.Lock()
        self.destructed = False
        self.provision_depth = 0

    async def _optimize(self, expr: Expr):
        """
        this finds duplicated expr in the node and replace it with Cache Node.
        """

        def solve_evaled_injected(expr: Expr):
            match expr:
                case Object(object(__expr__=expr)):
                    return expr
                case _:
                    return expr

        replaced = walk_replace(expr, solve_evaled_injected)
        replaced = walk_replace(replaced, lambda x: Cache(x))
        return replaced

    async def eval_expr(self, expr: Expr, cxt: ProvideContext):
        assert isinstance(expr, Expr), f"expr must be Expr, got {expr} of type {type(expr)}"
        self._callback(EvalRequestEvent(cxt, expr))
        """
                    case EvaledInjected(val, ast):
                expr = await self._optimize(ast)
                return await self.eval_expr(expr)
            case Injected() as i_tgt:
                return await self._provide_providable(BindInjected(i_tgt))
                            case IBind():
                deps = await resolve_deps(tgt.dependencies)
                return await tgt.provide(ProvideContext(self, key=tgt, parent=root_cxt), deps)
        """
        try:
            match expr:
                case Cache(src):
                    k = hash(src)
                    async with self.eval_locks[k]:
                        if k in self.eval_memos:
                            res = self.eval_memos[k]
                        else:
                            new_cxt = ProvideContext(self, key=StrBindKey(f"__eval__{k}"), parent=cxt)
                            res = await self.eval_expr(src, new_cxt)
                            self.eval_memos[k] = res

                case Object(DelegatedVar(value, cxt)):
                    new_cxt = ProvideContext(self, key=StrBindKey(f"__eval__{value}"), parent=cxt)
                    res = await self.eval_expr(value, new_cxt)
                case Object(EvaledInjected(val, ast)):
                    expr = await self._optimize(ast)
                    new_cxt = ProvideContext(self, key=StrBindKey(f"__eval__{val}"), parent=cxt)
                    res = await self.eval_expr(expr, new_cxt)
                case Object(Injected() as _injected):
                    new_cxt = ProvideContext(self, key=StrBindKey(f"__eval__{_injected}"), parent=cxt)
                    bind = BindInjected(_injected)
                    deps = await self.resolve_deps(bind.dependencies, new_cxt)
                    res = await bind.provide(new_cxt, deps)
                case Object(x):
                    res = x
                case Call(f, args, kwargs) as call:
                    res = await self._resolve_call_prev(call, cxt)
                case BiOp(op, left, right):
                    new_cxt = ProvideContext(self, key=StrBindKey(f"__eval__{left}"), parent=cxt)
                    left, right = await asyncio.gather(self.eval_expr(left, new_cxt), self.eval_expr(right, new_cxt))
                    res = OPERATORS[op](left, right)
                case UnaryOp('await', data):
                    new_cxt = ProvideContext(self, key=StrBindKey(f"__eval__{data}"), parent=cxt)
                    data = await self.eval_expr(data, new_cxt)
                    res = await data
                case UnaryOp(name, data):
                    new_cxt = ProvideContext(self, key=StrBindKey(f"__eval__{data}"), parent=cxt)
                    data = await self.eval_expr(data, new_cxt)
                    res = UNARY_OPS[name](data)
                case Attr(data, name):
                    new_cxt = ProvideContext(self, key=StrBindKey(f"__eval__{data}"), parent=cxt)
                    data = await self.eval_expr(data, new_cxt)
                    res = getattr(data, name)
                case GetItem(data, key):
                    new_cxt = ProvideContext(self, key=StrBindKey(f"__eval__{data}"), parent=cxt)
                    data, key = await asyncio.gather(self.eval_expr(data, new_cxt), self.eval_expr(key, new_cxt))
                    res = data[key]
                case _:
                    raise TypeError(
                        f"expr must be Object, Call, BiOp, UnaryOp, Attr or GetItem, got {expr} of type {type(expr)}")
            self._callback(EvalResultEvent(cxt, expr, res))
        except Exception as e:
            raise e
        # except EvaluationError as e:
        #     raise EvaluationError(cxt, expr, cause_expr=e.cause_expr, src=e.src) from e.src
        # except Exception as e:
        #     raise EvaluationError(cxt, expr, cause_expr=expr, src=e) from e

        return res

    async def _resolve_call_prev(self, call: Call, cxt):
        args = call.args
        kwargs = call.kwargs
        f = call.func
        new_cxt = ProvideContext(self, key=StrBindKey(f"__eval__{f}"), parent=cxt)
        args = asyncio.gather(*[self.eval_expr(a, new_cxt) for a in args])
        keys = list(kwargs.keys())
        values = asyncio.gather(*[self.eval_expr(v, new_cxt) for v in kwargs.values()])
        f, args, values = await asyncio.gather(self.eval_expr(f, new_cxt), args, values)
        kwargs = dict(zip(keys, values))
        self._callback(CallInEvalStart(cxt, call))
        # we cannot actually do *args **kwargs, due to complicated signature of f.
        # but is there a way to tell how the arguments are passed?
        # signature: (d1, d2, /, a, b, *args,c=7, **kwargs)
        # call_sig: (1,2,3,4,5)
        # ends up : (3,4,5,a=1,b=2), which is correct,
        # but it becomes args = (3,4,5), kwargs=(a=1,b=2)
        # so, doing f(*args,**kwargs) will end up with f(3,4,5, a=1, b=2)
        # this is unexpected for the user, sice the user expects f(1,2,3,4,5)
        # to fix this, we need to convert kwargs to args considering the signature.
        res = f(*args, **kwargs)
        # logger.info(f"{args=} {kwargs=}")
        self._callback(CallInEvalEnd(cxt, call, res))
        return res

    async def _provide(self, key: IBindKey, cxt: ProvideContext, provider=None):
        # we need to think which one to ask provider
        # if we have the binding for the key, use our own scope
        if provider is None:
            provider = self._provide

        async with self.locks.get(key):
            self._callback(RequestEvent(cxt, key))
            if key in self.objects:
                data = self.objects[key]
                self._callback(ProvideEvent(cxt, key, data))
                return data
            overridden_keys = set(self.design.keys())
            d = self._design_from_ancestors()
            bind: IBind = d.bindings[key]
            dep_keys = set(bind.complete_dependencies)

            if dep_keys & overridden_keys or key in overridden_keys:
                # Create instance, when the deps or the key is overriden
                # we are responsible for providing this
                # bind: IBind = self.design.bindings[key]
                # dep_keys = list(bind.dependencies)
                tasks = []
                for dep_key in dep_keys:
                    n_cxt = ProvideContext(self, key=dep_key, parent=cxt)
                    tasks.append(provider(dep_key, n_cxt))
                res = await asyncio.gather(*tasks)
                deps = dict(zip(dep_keys, res))
                self._callback(DepsReadyEvent(cxt, key, deps))
                data = await bind.provide(cxt, deps)
                self.objects[key] = data
                # show_data = str(data)[:100]
                # logger.info(f"{cxt.trace_str} := {show_data}")
                self._callback(ProvideEvent(cxt, key, data))
                return data
            else:
                if self.parent is not None:
                    return await self.parent._provide(key, cxt, provider)
                else:
                    raise KeyError(f"Key {key} not found in design in {cxt.trace_str}")

    def child_session(self, overrides: "Design"):
        return AsyncResolver(overrides, parent=self)

    async def resolve_deps(self, keys: set[IBindKey], cxt):
        tasks = [self._provide(k, ProvideContext(self, key=k, parent=cxt)) for k in keys]
        return {k: v for k, v in zip(keys, await asyncio.gather(*tasks))}

    async def validate(self, key: IBindKey, value: Any):
        validator: Optional[ProvisionValidator] = self.design.validations.get(key, None)
        if validator is not None:
            res = await validator(key, value)
            match res:
                case ValFailure(e) as vf:
                    raise DependencyValidationError(f"Validation failed for {key}", cause=vf)
                case ValSuccess() as vs:
                    logger.success(f"validation passed for {key}")
                case _:
                    raise TypeError(f"validator must return ValFailure or ValSuccess, got {res}")
        else:
            pass
            #logger.debug(f"no validator found for {str(key)[:100]} from {self.design}")

    async def _provide_providable(self, tgt: Providable):
        root_cxt = ProvideContext(self, key=StrBindKey("__root__"), parent=None)

        match tgt:
            case str():
                key = StrBindKey(tgt)
                res = await self._provide(key, ProvideContext(self, key=key, parent=root_cxt))
                await self.validate(key, res)
                return res
            case IBindKey():
                res = await self._provide(tgt, ProvideContext(self, key=tgt, parent=root_cxt))
                await self.validate(tgt, res)
                return res
            case DelegatedVar(value, cxt) as dv:
                # return await self._provide_providable(tgt.eval())
                expr = await self._optimize(dv.eval().ast)
                key = StrBindKey(f"{show_expr(value)}")
                new_cxt = ProvideContext(self, key=StrBindKey(f"{show_expr(value)}"), parent=root_cxt)
                res = await self.eval_expr(expr, new_cxt)
                await self.validate(key, res)
                return res
            case EvaledInjected(val, ast):
                expr = await self._optimize(ast)
                key = StrBindKey(f"{show_expr(ast)}")
                new_cxt = ProvideContext(self, key=key, parent=root_cxt)
                res = await self.eval_expr(expr, new_cxt)
                await self.validate(key, res)
                return res
            case Injected() as i_tgt:
                return await self._provide_providable(BindInjected(i_tgt))
            case IBind():
                deps = await self.resolve_deps(tgt.dependencies, root_cxt)
                res = await tgt.provide(ProvideContext(self, key=None, parent=root_cxt), deps)
                return res
            case func if inspect.isfunction:
                deps = extract_dependency(func)
                keys = {StrBindKey(d) for d in deps}
                deps = await self.resolve_deps(keys, root_cxt)
                kwargs = {k.name: v for k, v in deps.items()}
                data = tgt(**kwargs)
                if inspect.iscoroutinefunction(tgt):
                    return await data
                else:
                    return data
            case _:
                raise TypeError(f"tgt must be str, IBindKey, Callable or IBind, got {tgt}")

    def _design_from_ancestors(self):
        from pinjected import EmptyDesign
        if self.parent is None:
            p_design = EmptyDesign
        else:
            p_design = self.parent._design_from_ancestors()
        return p_design + self.design

    async def validate_provision(self, tgt: Providable):
        logger.debug(f"validating provision...")
        from pinjected import providers
        d = self._design_from_ancestors()
        errors = []
        match tgt:
            case Injected():
                tmp_design = d + providers(__root__=tgt)
                digraph: DIGraph = DIGraph(tmp_design)
                errors = list(digraph.di_dfs_validation("__root__"))
            case str():
                digraph: DIGraph = DIGraph(d)
                errors = list(digraph.di_dfs_validation(tgt))
            case DelegatedVar() as dv:
                tmp_design = d + providers(__root__=tgt)
                digraph: DIGraph = DIGraph(tmp_design)
                errors = list(digraph.di_dfs_validation("__root__"))
            case f if callable(f):
                tmp_design = d + providers(__root__=tgt)
                digraph: DIGraph = DIGraph(tmp_design)
                errors = list(digraph.di_dfs_validation("__root__"))

        if errors:
            raise DependencyResolutionError(f"Errors in dependency resolution:\n{pformat(errors)}\n", causes=errors)
        logger.debug(f"provision validated.")

    async def provide(self, tgt: Providable):
        self.provision_depth += 1
        try:
            if self.provision_depth == 1:
                async with TaskGroup() as tg:
                    await self.validate_provision(tgt)
                    match tgt:
                        case EvaledInjected(val, ast):
                            repr = show_expr(ast)
                        case DelegatedVar(value, cxt) as dv:
                            repr = show_expr(dv.eval().ast)
                        case _:
                            repr = str(tgt)
                    logger.info(f"providing {repr}")
                    tg_key = StrBindKey('__task_group__')
                    self.objects[tg_key] = tg
                    res = await self._provide_providable(tgt)
                    del self.objects[tg_key]
                return res
            else:
                return await self._provide_providable(tgt)
        finally:
            self.provision_depth -= 1

    async def provide_or(self, tgt: Providable, default):
        try:
            return await self.provide(tgt)
        except Exception as e:
            return default

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
            if destructions:
                logger.info(f"waiting for {len(destructions)} destructors to finish.")
                results = await asyncio.gather(*destructions)
                logger.success(f"all destructors finished with results:{results}")
                logger.success(f"Resolver destructed")
            else:
                results = []
            self.destructed = True
            return results


@dataclass
class ResolveStatus:
    key: Any
    kind: str  # eval or provide
    status: str
    start: Optional[datetime.datetime]
    end: Optional[datetime.datetime]


@dataclass
class BaseResolverCallback(IResolverCallback):
    def __post_init__(self):
        self.request_status: dict[IBindKey, str] = {}
        self.logger = logger.opt(colors=True, ansi=True)
        self.eval_status: dict[str, str] = {}
        self.total_status: dict[Union[IBindKey, str]] = {}

    def __call__(self, event: ResolverEvent):
        if isinstance(event, RequestEvent):
            self.on_request(event)
        elif isinstance(event, ProvideEvent):
            self.on_provide(event)
        elif isinstance(event, DepsReadyEvent):
            self.on_deps_ready(event)
        elif isinstance(event, EvalRequestEvent):
            self.on_eval_request(event)
        elif isinstance(event, EvalResultEvent):
            self.on_eval_result(event)
        elif isinstance(event, CallInEvalStart):
            self.on_call_in_eval_start(event)
        elif isinstance(event, CallInEvalEnd):
            self.on_call_in_eval_end(event)
        else:
            raise TypeError(f"event must be RequestEvent or ProvideEvent, got {event}")
        self.logger.info(f"{self.total_status_string()}")

    def provider_status_string(self):
        succeeded = [k for k in self.request_status if self.request_status[k] == "provided"]
        running = [k for k in self.request_status if self.request_status[k] == "running"]
        waiting = [k for k in self.request_status if self.request_status[k] == "waiting"]
        succeeded = ", ".join([self._colored_key(k) for k in succeeded])
        running = ", ".join([self._colored_key(k) for k in running])
        waiting = ", ".join([self._colored_key(k) for k in waiting])
        res = f"Provided: [{succeeded}]\nWaiting: [{waiting}]\nRunning: [{running}]"
        return res

    def eval_status_string(self):
        awaiting = [k for k in self.eval_status if self.eval_status[k] == "await"]
        done = [k for k in self.eval_status if self.eval_status[k] == "done"]
        evaluating = [k for k in self.eval_status if self.eval_status[k] == "eval"]
        calling = [k for k in self.eval_status if self.eval_status[k] == "calling"]
        awaiting = ", ".join([self._colored_eval_key(k) for k in awaiting])
        done = ", ".join([self._colored_eval_key(k) for k in done])
        evaluating = ", ".join([self._colored_eval_key(k) for k in evaluating])
        calling = ", ".join([self._colored_eval_key(k) for k in calling])
        res = f"Awaiting:\t [{awaiting}]\nEvaluating:\t [{evaluating}]\nDone:\t\t [{done}]\nCalling:\t [{calling}]"
        return res

    def total_status_string(self):
        res = "\n===== RESOLVER STATUS =====\n"
        for k, v in self.state_string_dict().items():
            vals = list(v.values())
            res += f"{k}:\t"
            if vals:
                res += f"[{', '.join(vals[:10])}]\n"
            else:
                res += "[]\n"
            if len(v.values()) >= 10:
                res += f"and {len(vals) - 10} more...\n"
        return res

    def state_string_dict(self):
        provided = [k for k in self.request_status if self.request_status[k] == "provided"]
        provided = {k: self._colored_key(k) for k in provided[:10]}
        running = [k for k in self.request_status if self.request_status[k] == "running"]
        running = {k: self._colored_key(k) for k in running}
        waiting = [k for k in self.request_status if self.request_status[k] == "waiting"]
        waiting = {k: self._colored_key(k) for k in waiting}

        eval_awaiting = [k for k in self.eval_status if self.eval_status[k] == "await"]
        eval_awaiting = {k: self._colored_eval_key(k) for k in eval_awaiting}
        eval_done = [k for k in self.eval_status if self.eval_status[k] == "done"]
        eval_done = {k: self._colored_eval_key(k) for k in eval_done}
        # eval_done = dict(TOTAL=f"{len(eval_done)} evaluations done.")

        eval_evaluating = [k for k in self.eval_status if self.eval_status[k] == "eval"]
        eval_evaluating = {k: self._colored_eval_key(k) for k in eval_evaluating}
        eval_calling = [k for k in self.eval_status if self.eval_status[k] == "calling"]
        eval_calling = {k: self._colored_eval_key(k) for k in eval_calling}
        return dict(
            Pending=waiting,
            Provided=provided,
            Running=running,
            Evaluating=eval_evaluating,
            Eval_Await=eval_awaiting,
            Eval_Call=eval_calling,
            Eval_Done=eval_done,
        )

    def _colored_eval_key(self, key: str):
        match self.eval_status[key]:
            case "await":
                return f"<yellow>{key}</yellow>"
            case "done":
                return f"<green>{key}</green>"
            case "eval":
                return f"<magenta>{key}</magenta>"
            case "calling":
                return f"<bold><yellow>{key}</yellow></bold>"

    def _colored_key(self, key: IBindKey):
        s = key.ide_hint_string()
        match self.request_status[key]:
            case "waiting":
                return f"<cyan>{s}</cyan>"
            case "running":
                return f"<yellow>{s}</yellow>"
            case "provided":
                return f"<green>{s}</green>"
            case _:
                raise ValueError(f"Unknown status {self.request_status[key]}")

    def on_request(self, event: RequestEvent):
        self.request_status[event.key] = "waiting"
        self.logger.info(f"{self.clean_msg(event.cxt.trace_str)}")
        self.total_status[event.key] = ResolveStatus(event.key, "provide", "waiting", datetime.datetime.now(), None)

    def on_provide(self, event: ProvideEvent):
        self.total_status[event.key].status = "provided"
        self.request_status[event.key] = "provided"
        data_str = str(event.data)[:50]
        data_str = self.clean_msg(data_str)
        self.logger.info(f"{self.clean_msg(event.cxt.trace_str)} := {data_str}")
        # self.logger.info(f"{self.provider_status_string()}")

    def on_deps_ready(self, event: DepsReadyEvent):
        self.total_status[event.key].status = "running"
        self.request_status[event.key] = "running"
        self.logger.info(f"{self.clean_msg(event.cxt.trace_str)}")
        # self.logger.info(f"{self.provider_status_string()}")

    def clean_msg(self, msg):
        return msg.replace("<", "\<").replace(">", "\>")

    def on_eval_request(self, event):
        expr = self.expr_repr(event.expr)
        match event.expr:
            case Cache(_):
                return
            case Call():
                self.total_status[expr] = ResolveStatus(expr, "eval", "calling", datetime.datetime.now(), None)
                self.eval_status[expr] = "calling"
            case UnaryOp('await', _):
                self.total_status[expr] = ResolveStatus(expr, "eval", "await", datetime.datetime.now(), None)
                self.eval_status[expr] = "await"
                # self.logger.debug(f"await\t -> <red>{expr}</red>")
            case _:
                self.total_status[expr] = ResolveStatus(expr, "eval", "eval", datetime.datetime.now(), None)
                self.eval_status[expr] = "eval"
                # self.logger.debug(f"eval\t-> <magenta>{expr}</magenta>")
        # self.logger.info(f"\n{self.eval_status_string()}")

    def expr_repr(self, e):
        msg = show_expr(e)
        msg = self.clean_msg(msg)
        if len(msg) >= 50:
            msg = msg[:25] + "..." + msg[-25:]
        return msg

    def on_eval_result(self, event):
        expr = self.expr_repr(event.expr)
        res_msg = self.clean_msg(str(event.result)[:50])
        match event.expr:
            case Cache(_):
                return
            case Call():

                self.logger.success(f"call\t<- <magenta>{expr}</magenta>\t:= {res_msg}")
            case UnaryOp('await', _):
                self.logger.success(f"await <- <red>{expr}</red> := {res_msg}")
            case _:
                self.logger.debug(f"eval<- <magenta>{expr}</magenta> := {res_msg}")
        self.total_status[expr].status = "done"

        self.eval_status[expr] = "done"
        # self.logger.info(f"\n{self.eval_status_string()}")

    def on_call_in_eval_start(self, event: CallInEvalStart):
        expr_str = self.expr_repr(event.expr)
        self.logger.debug(f"call\t-> <magenta>{expr_str}</magenta>")

    def on_call_in_eval_end(self, event: CallInEvalEnd):
        expr_str = self.expr_repr(event.expr)
        self.logger.success(f"call\t<- <magenta>{expr_str}</magenta>\t:= {self.clean_msg(str(event.result)[:100])}")


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
