import asyncio
import inspect
from collections import defaultdict
from dataclasses import dataclass, field
from pprint import pformat
from traceback import FrameSummary
from typing import Optional, Dict, Any, Callable, Union, ParamSpec, TypeVar

from returns.future import FutureResultE, FutureResult
from returns.io import IOSuccess, IOResultE, IOFailure
from returns.maybe import Nothing, Maybe
from returns.pipeline import is_successful
from returns.primitives.tracing import collect_traces
from returns.unsafe import unsafe_perform_io

from pinjected import Injected
from pinjected.compatibility.task_group import TaskGroup
from pinjected.di.app_injected import walk_replace, EvaledInjected
from pinjected.di.design_spec.protocols import DesignSpec, BindSpec
from pinjected.di.expr_util import Expr, Object, Cache, Call, BiOp, UnaryOp, Attr, GetItem, show_expr
from pinjected.di.implicit_globals import IMPLICIT_BINDINGS
from pinjected.di.injected import extract_dependency
from pinjected.di.proxiable import DelegatedVar
from pinjected.exceptions import DependencyResolutionError, CyclicDependency, DependencyResolutionFailure, \
    DependencyValidationError
from pinjected.pinjected_logging import logger
from pinjected.v2.binds import BindInjected, IBind
from pinjected.v2.callback import IResolverCallback
from pinjected.v2.events import ResolverEvent, EvalRequestEvent, EvalResultEvent, CallInEvalStart, CallInEvalEnd, \
    RequestEvent, ProvideEvent, DepsReadyEvent
from pinjected.v2.keys import IBindKey, StrBindKey, DestructorKey
from pinjected.v2.provide_context import ProvideContext
from pinjected.v2.resolver import AsyncLockMap, OPERATORS, UNARY_OPS, Providable, EvaluationError
from pinjected.visualize_di import DIGraph

StaticProvisionError = Union[CyclicDependency, DependencyResolutionFailure]

P = ParamSpec('P')
T = TypeVar('T')


def maybe_fre_to_fre(
        f: Maybe[Callable[P, FutureResultE[str]]],
        default: FutureResultE = FutureResult.from_failure(None)
) -> Callable[P, FutureResultE[str]]:
    def impl(*args: P.args, **kwargs: P.kwargs) -> FutureResultE[str]:
        if f is Nothing:  # Changed == to is for singleton comparison
            return default
        else:
            res = f.unwrap()(*args, **kwargs)
            assert isinstance(res, FutureResult), f"expected FutureResultE got {res}"
            return res  # Added missing return statement

    return impl


def create_tb(failure: IOFailure) -> str:
    traces: list[inspect.FrameInfo] = failure.trace
    frame_summaries = []
    for frame in traces:
        # Create a FrameSummary for each frame
        summary = FrameSummary(
            filename=frame.filename,
            lineno=frame.lineno,
            name=frame.function,
            line=frame.line if hasattr(frame, 'line') else None,
        )
        frame_summaries.append(summary)
    import traceback
    tb = traceback.format_list(frame_summaries)
    return "".join(tb)


@dataclass
class AsyncResolver:
    # design provides actual bindings for the resolver.
    design: "Design"
    parent: Optional["AsyncResolver"] = None
    objects: Dict[IBindKey, Any] = field(default_factory=dict)
    locks: AsyncLockMap = field(default_factory=AsyncLockMap)
    callbacks: list[IResolverCallback] = field(default=None)
    spec: DesignSpec = field(default=DesignSpec.empty())
    use_implicit_bindings:bool = field(default=True)

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
        if self.use_implicit_bindings:
            self.design = Design.from_bindings(IMPLICIT_BINDINGS) + self.design

        from pinjected import design
        async def dummy():
            raise RuntimeError('This should never be instantiated')

        dummy = Injected.bind(dummy)

        # maybe,,, we can obtain __pinjected_provision_callback__ from design.
        # but provision involves instantiating this resolver, resulting in recursion.
        # The solution is to introduce a 'phase' for provision
        # 1. preparation phase, instantiate all stuff like __pinjected_....__.
        # 2. user provision phase, where user can provide stuff. we use __pinjected_...__ to provide stuff.
        # I think we should stick to constructor injection for simplicity.

        self.design = self.design + design(
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

    def _a_validate(self, key: IBindKey, value) -> FutureResultE[str]:
        # hmm, we get Maybe[Maybe[Callable[[T],FutureResultE[str]]]
        # and we want to convert it to T->FutureResultE[str]
        # oh wait we can postpone awaiting
        maybe_spec: Maybe[BindSpec] = self.spec.get_spec(key)
        maybe_validator: Maybe[Callable] = maybe_spec.bind(lambda x: x.validator)
        return maybe_fre_to_fre(maybe_validator, default=FutureResult.from_value("No validation provided"))(key, value)

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
        except EvaluationError as e:
            raise EvaluationError(cxt, expr, cause_expr=e.cause_expr, src=e.src) from e.src
        except Exception as e:
            raise EvaluationError(cxt, expr, cause_expr=expr, src=e) from e

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
                validation: IOResultE[str] = await self._a_validate(key, data)
                if not is_successful(validation):
                    import traceback
                    tb = create_tb(validation)
                    raise DependencyValidationError(f"Validation failed for {key} {validation.failure()}: {tb}",
                                                    cause=validation)
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

    async def _provide_providable(self, tgt: Providable):
        root_cxt = ProvideContext(self, key=StrBindKey("__root__"), parent=None)

        match tgt:
            case str():
                key = StrBindKey(tgt)
                res = await self._provide(key, ProvideContext(self, key=key, parent=root_cxt))
                return res
            case IBindKey():
                res = await self._provide(tgt, ProvideContext(self, key=tgt, parent=root_cxt))
                return res
            case DelegatedVar(value, cxt) as dv:
                # return await self._provide_providable(tgt.eval())
                expr = await self._optimize(dv.eval().ast)
                key = StrBindKey(f"{show_expr(value)}")
                new_cxt = ProvideContext(self, key=StrBindKey(f"{show_expr(value)}"), parent=root_cxt)
                res = await self.eval_expr(expr, new_cxt)
                return res
            case EvaledInjected(val, ast):
                expr = await self._optimize(ast)
                key = StrBindKey(f"{show_expr(ast)}")
                new_cxt = ProvideContext(self, key=key, parent=root_cxt)
                res = await self.eval_expr(expr, new_cxt)
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

    async def a_find_provision_errors(self, tgt: Providable) -> list[StaticProvisionError]:
        from pinjected import design
        d = self._design_from_ancestors()
        errors = []
        match tgt:
            case Injected():
                tmp_design = d + design(__root__=tgt)
                digraph: DIGraph = DIGraph(tmp_design,use_implicit_bindings=self.use_implicit_bindings)
                errors = list(digraph.di_dfs_validation("__root__"))
            case str():
                digraph: DIGraph = DIGraph(d,use_implicit_bindings=self.use_implicit_bindings)
                errors = list(digraph.di_dfs_validation(tgt))
            case DelegatedVar() as dv:
                tmp_design = d + design(__root__=tgt)
                digraph: DIGraph = DIGraph(tmp_design,use_implicit_bindings=self.use_implicit_bindings)
                errors = list(digraph.di_dfs_validation("__root__"))
            case f if callable(f):
                tmp_design = d + design(__root__=tgt)
                digraph: DIGraph = DIGraph(tmp_design,use_implicit_bindings=self.use_implicit_bindings)
                errors = list(digraph.di_dfs_validation("__root__"))
        return errors

    async def a_check_resolution(self, tgt: Providable):
        if errors := await self.a_find_provision_errors(tgt):
            # here we can use spec to provide more helpful error messages.
            drfs = [drf for drf in errors if isinstance(drf, DependencyResolutionFailure)]
            cyclics = [c for c in errors if isinstance(c, CyclicDependency)]
            message = ""
            if drfs:
                header = f"========== Missing Dependencies for {tgt} ==========\n"
                len_header = len(header)
                missing_keys = {drf.key for drf in drfs}
                message += header
                message += f"Missing Dependencies: {missing_keys}\n"
                message += "-" * len_header + "\n"
                for e in drfs:
                    key, trace, cause = e.key, e.trace, e.cause
                    message += f"Trace {e.trace_str()}: {e.cause}\n"
                    key = StrBindKey(key)
                    spec: Maybe[BindSpec] = self.spec.get_spec(key)
                    maybe_provider: Maybe[Callable[[IBindKey], FutureResultE[str]]] = spec.bind(
                        lambda x: x.spec_doc_provider
                    )
                    fut_msg: IOResultE[str] = await maybe_fre_to_fre(maybe_provider)(key)
                    doc_msg = unsafe_perform_io(fut_msg.value_or("No documentation provided"))
                    message += f"Documentation:\n"
                    message += f"  {doc_msg}\n"
                    message += "-" * len_header + "\n"
                message += "=" * len_header + "\n"
            if cyclics:
                header = f"========== Cyclic Dependencies for {tgt} ==========\n"
                len_header = len(header)
                message += header
                for c in cyclics:
                    message += f"{c}\n"
                message += "=" * len_header + "\n"

            raise DependencyResolutionError(f"Errors in dependency resolution:\n{message}", causes=errors)

    async def provide(self, tgt: Providable):
        with collect_traces():
            self.provision_depth += 1
            try:
                if self.provision_depth == 1:
                    async with TaskGroup() as tg:
                        await self.a_check_resolution(tgt)
                        match tgt:
                            case EvaledInjected(val, ast):
                                repr = show_expr(ast)
                            case DelegatedVar(value, cxt) as dv:
                                repr = show_expr(dv.eval().ast)
                            case _:
                                repr = str(tgt)
                        if len(repr) > 100:
                            repr = repr[:50] + "..." + repr[-50:] + f"({len(repr) - 100} more)"
                        logger.info(f"providing {repr}")
                        tg_key = StrBindKey('__task_group__')
                        self.objects[tg_key] = tg
                        res = await self._provide_providable(tgt)
                        del self.objects[tg_key]
                    return res
                else:
                    return await self._provide_providable(tgt)
            except Exception as e:
                import pinjected.compatibility.task_group
                if hasattr(pinjected.compatibility.task_group, 'ExceptionGroup'):
                    logger.debug(f"using compatibility.task_group.ExceptionGroup")
                    EG = pinjected.compatibility.task_group.ExceptionGroup
                else:
                    logger.debug(f"using builtin ExceptionGroup")
                    EG = ExceptionGroup
                if isinstance(e, EG):
                    if len(e.exceptions) == 1:
                        logger.debug(f"raising first exception from {[type(e) for e in e.exceptions]}")
                        raise e.exceptions[0]
                raise e
            finally:
                self.provision_depth -= 1

    async def provide_or(self, tgt: Providable, default):
        try:
            return await self.provide(tgt)
        except DependencyResolutionError as e:
            return default

    def to_blocking(self):
        from pinjected.v2.blocking_resolver import Resolver
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
