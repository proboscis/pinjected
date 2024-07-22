import asyncio
import inspect
import threading
from abc import ABCMeta, abstractmethod, ABC
from concurrent.futures import Future
from dataclasses import dataclass, field
from functools import lru_cache
from itertools import chain
from pathlib import Path
from pprint import pformat
from typing import Union, Callable, TypeVar, List, Any, Generic, Set, Dict

from returns.maybe import Nothing, Maybe, Some
from returns.result import safe, Result, Failure, Success
from rich.console import Console
from rich.panel import Panel

from pinjected.di.app_injected import EvaledInjected
from pinjected.di.expr_util import Expr
from pinjected.di.designed import Designed
from pinjected.di.injected import Injected, InjectedByName, InjectedFunction
from pinjected.di.metadata.bind_metadata import BindMetadata
from pinjected.di.metadata.location_data import ModuleVarLocation
from pinjected.di.proxiable import DelegatedVar
from pinjected.di.sessioned import Sessioned
from pinjected.exceptions import DependencyResolutionFailure, DependencyResolutionError
from pinjected.graph_inspection import DIGraphHelper
from pinjected.providable import Providable
from pinjected.v2.binds import IBind
from pinjected.visualize_di import DIGraph

T = TypeVar("T")


class MissingDependencyException(Exception):
    @staticmethod
    def create_message(deps: List[DependencyResolutionFailure]):
        msgs = [item.explanation_str() for item in deps]
        lines = '\n'.join(msgs)
        return f"Missing dependency. failures:\n {lines}."

    @staticmethod
    def create(deps: List[DependencyResolutionFailure]):
        return MissingDependencyException(MissingDependencyException.create_message(deps))


class IObjectGraphFactory(ABC):
    def create(self) -> "IObjectGraph":
        pass


@dataclass
class OGFactoryByDesign(IObjectGraphFactory):
    src: "Design"

    def create(self) -> "IObjectGraph":
        return self.src.to_graph()


class IObjectGraph(metaclass=ABCMeta):
    @abstractmethod
    def provide(self, target: Providable, level: int = 2):
        pass

    def __getitem__(self, item: Providable):
        return self.provide(item, level=3)

    @abstractmethod
    def child_session(self, overrides=None) -> "IObjectGraph":
        """
        bindings that are explicit in the overrides are always recreated.
        implicit bindings are created if it is not created in parent. and will be discarded after session.
        else from parent.
        so, implicit bindings that are instantiated at the moment this function is called will be used if not explicitly overriden.
        invalidation is not implemented yet.
        I want the bindings that are dependent on the overriden keys to be reconstructed.
        :param overrides:
        :return:
        """
        raise NotImplementedError()

    def run(self, f):
        argspec = inspect.getfullargspec(f)
        assert "self" not in argspec.args, f"self in {argspec.args}, of {f}"
        # logger.info(self)
        assert argspec.varargs is None
        kwargs = {k: self.provide(k) for k in argspec.args}
        return f(**kwargs)

    def proxied(self, providable: Providable) -> DelegatedVar[Sessioned]:
        from pinjected.di.sessioned import sessioned_ast_context
        designed = self._providable_to_designed(providable)
        item = Sessioned(self, designed)
        ctx = sessioned_ast_context(self)
        from pinjected.di.expr_util import Object
        return DelegatedVar(Object(item), ctx)

    def sessioned(self, target: Providable) -> DelegatedVar[Union[object, T]]:
        match target:
            case str():
                return self.sessioned(Injected.by_name(target))
            case Injected():
                return self.sessioned(Designed.bind(target))
            case provider if callable(provider):
                return self.sessioned(Injected.bind(provider))
            case Designed():
                val = SessionValue(self, target)
                ctx = sessioned_value_proxy_context(self, val.session)
                return DelegatedVar(val, ctx)
            case DelegatedVar():
                return self.sessioned(target.eval())
            case _:
                raise TypeError(f"Unknown target:{target} queried for DI.")

    def _providable_to_designed(self, target: Providable):
        match target:
            case str():
                return self._providable_to_designed(Injected.by_name(target))
            case Injected():
                return Designed.bind(target)
            case Designed():
                return target
            case DelegatedVar():
                return self._providable_to_designed(target.eval())
            case provider if callable(provider):
                return self._providable_to_designed(Injected.bind(provider))
            case _:
                raise TypeError(f"Unknown target:{target} queried for DI.")

    @property
    @abstractmethod
    def factory(self) -> IObjectGraphFactory:
        pass

    @property
    @abstractmethod
    def design(self):
        pass

    @property
    @abstractmethod
    def resolver(self) -> "DependencyResolver":
        pass


# using async was not a good Idea since all the function needs to be assumed a coroutine.
# we don't assume the provider function is a coroutine.
@dataclass
class ProvideEvent:
    trace: list[str]  # stack of keys currently being provided
    kind: str  # "provide" or "request"
    data: Any = field(default=None)  # provided data when kind == "provide"


class IScope:
    @abstractmethod
    def provide(self, key, provider_func: Callable[[], Any], trace: List) -> Any:
        pass

    @abstractmethod
    def __contains__(self, item):
        raise NotImplementedError()

    @property
    @abstractmethod
    def trace_logger(self):
        pass

    @staticmethod
    def default_trace_logger(event: ProvideEvent):
        from loguru import logger
        match event:
            case ProvideEvent(trace, "request", data=None):
                logger.info(f"{' -> '.join(trace)}")
            case ProvideEvent(trace, "provide", data=[*items]) if len(items) > 100:
                logger.info(f"{' <- '.join(trace)} = LARGE LIST({len(items)} items)")
            case ProvideEvent(trace, "provide", data=[*items]):
                logger.info(f"{' <- '.join(trace)} = {pformat(items)[:100]}")
            case ProvideEvent(trace, "provide", data=data):
                try:
                    buf = str(data)[:100]
                    logger.info(f"{' <- '.join(trace)} = {buf}")
                except Exception as e:
                    logger.error(f"failed to log {trace} with {e}, while providing {' <- '.join(trace)}")


def trace_string(trace: list[str]):
    # res = "\n"
    # for i, item in enumerate(trace):
    #     res += f"{i * '  '}{item} -> \n"
    # return res
    return f" -> ".join(trace)


@dataclass
class RichTraceLogger:
    from rich.console import Console
    console: Console = field(default_factory=lambda: Console(stderr=True))

    def __call__(self, event: ProvideEvent):
        match event:
            case ProvideEvent(trace, "request", data=None):
                self.console.log(f"provide trace:{trace}")
                self.console.log(Panel(trace_string(trace)))
            case ProvideEvent(trace, "provide", data):
                key = trace[-1]
                self.console.log(Panel(trace_string(trace)))
                self.console.log(Panel(pformat(data)))
                # self.console.log(self.value_table(self.values))


@dataclass
class MScope(IScope):
    cache: dict[str, Any] = field(default_factory=dict)
    _trace_logger: Callable[[ProvideEvent], None] = field(default=None)

    def __post_init__(self):
        self._trace_logger = self._trace_logger or self.default_trace_logger
        # self.trace_logger = self.trace_logger or RichTraceLogger()

    @property
    def trace_logger(self):
        return self._trace_logger

    def __getstate__(self):
        raise NotImplementedError("MScope is not serializable")

    def provide(self, key, provider: Callable[[], Any], trace: List) -> Any:
        # with self.lock:
        self.trace_logger(ProvideEvent(trace, "request"))
        if key in self.cache:
            self.trace_logger(ProvideEvent(trace, "provide", data=self.cache[key]))
            return self.cache[key]
        assert isinstance(trace, list) and all(isinstance(item, str) for item in trace)
        assert trace[-1] == key
        res = provider()
        self.cache[key] = res
        res = self.cache[key]
        self.trace_logger(ProvideEvent(trace, "provide", data=res))
        return res

    def __contains__(self, item):
        return item in self.cache


@dataclass
class MChildScope(IScope):
    parent: IScope
    override_targets: set
    cache: dict[str, Any] = field(default_factory=dict)
    _trace_logger: Callable[[ProvideEvent], None] = field(default=None)

    def __post_init__(self):
        self._trace_logger = self._trace_logger or self.default_trace_logger
        # self.trace_logger = self.trace_logger or RichTraceLogger()

    @property
    def trace_logger(self):
        return self._trace_logger

    def __getstate__(self):
        raise NotImplementedError("MChildScope is not serializable")

    def provide(self, key, provider_func: Callable[[], Any], trace: List) -> Any:
        if key not in self.cache:
            if key in self.override_targets or key not in self.parent:
                # logger.info(f"providing from child:{' -> '.join(trace)}")
                self.trace_logger(ProvideEvent(trace, "request"))
                res = provider_func()
                self.cache[key] = res
                res = self.cache[key]
                self.trace_logger(ProvideEvent(trace, "provide", data=res))
                # logger.info(f"provided from child: {' <- '.join(trace)} = {str(res)[:100]}")
            else:
                self.cache[key] = self.parent.provide(key, provider_func, trace)
        return self.cache[key]

    def __contains__(self, item):
        return item in self.cache or item in self.parent


@dataclass
class OverridingScope(IScope):
    """
    This class overrides a given scope with a given set of keys.
    The overriden values will be returned if asked, instead of the original scope.
    """
    src: IScope
    overrides: Dict[str, Any]

    def provide(self, key, provider_func: Callable[[], Any], trace: List) -> Any:
        if key in self.overrides:
            return self.overrides[key]
        else:
            return self.src.provide(key, provider_func, trace)

    def __contains__(self, item):
        return item in self.overrides or item in self.src


class NoMappingError(Exception):
    def __init__(self, key):
        super().__init__(f"No mapping found for DI:{key}")
        self.key = key


@dataclass
class DependencyResolver:
    """
    okey I want to make a variant that uses IMPLICIT_BINDINGS when the target is not in the mapping.
    what we need is actually a str->Injected mapping.
    """
    src: "Design"

    def _to_injected(self, tgt: Providable):
        return providable_to_injected(tgt)

    def __post_init__(self):
        # gather things to build providers graph
        self.helper = DIGraphHelper(self.src)
        #
        self.mapping: dict[str, Injected] = self.helper.total_mappings()

        @lru_cache()
        def _memoized_provider(tgt: str):
            return self.mapping[tgt].get_provider()

        self.memoized_provider = _memoized_provider

        predefined = {"__final_target__"}

        @lru_cache()
        def _memoized_deps(tgt: str, include_dynamic=False):
            if tgt in predefined:
                return []
            if tgt not in self.mapping:
                raise NoMappingError(f"target {tgt} is not in the dependency injection mapping.")

            deps = self.mapping[tgt].dependencies()
            if include_dynamic:
                deps = set(deps) | set(self.mapping[tgt].dynamic_dependencies())
            return deps

        self.memoized_deps = _memoized_deps

    def _dfs(self, tgt: str,trace:list[str]=None, visited: set[str] = None, include_dynamic=False):
        if visited is None:
            visited = set()
        if tgt in visited:
            return
        if trace is None:
            trace = []
        trace += [tgt]
        visited.add(tgt)
        try:
            deps = self.memoized_deps(tgt, include_dynamic=include_dynamic)
        except NoMappingError as ke:
            from loguru import logger
            logger.error(f"failed to find dependency for {tgt} in {' -> '.join(trace)}")
            raise NoMappingError(f"failed to find dependency for {tgt} in {' -> '.join(trace)}") from ke
        yield tgt
        for dep in deps:
            yield from self._dfs(dep,trace, visited, include_dynamic=include_dynamic)

    def required_dependencies(self, providable: Providable, include_dynamic=False) -> Set[str]:
        tgt: Injected = self._to_injected(providable)
        first_deps = tgt.complete_dependencies if include_dynamic else tgt.dependencies()
        return set(chain(*[self._dfs(d, include_dynamic=include_dynamic) for d in first_deps]))

    def purified_design(self, providable: Providable):
        from pinjected import providers
        deps = self.required_dependencies(providable, include_dynamic=True)
        deps = {k: self.mapping[k] for k in deps}
        return providers(**deps)

    def _dependency_tree(self, tgt: str, trace: list[str] = None) -> Result[Dict[str, Result], Exception]:
        trace = trace or [tgt]
        try:
            res = dict()
            deps = self.memoized_deps(tgt)
            for d in deps:
                assert d not in trace, f"cycle detected: {d} is requested in {' -> '.join(trace)}"
                res[d] = self._dependency_tree(d, trace + [d])
            return Success(res)
        except NoMappingError as ke:
            from loguru import logger
            # msg = f"failed to find dependency for {tgt} in {' -> '.join(trace)}"
            return Failure(DependencyResolutionFailure(tgt, trace, ke))

            # raise RuntimeError(msg) from ke

    def dependency_tree(self, providable: Providable) -> Result[Dict[str, Result], Exception]:
        match providable:
            case str():
                return Success({providable: self._dependency_tree(providable)})
            case _:
                tgt: Injected = self._to_injected(providable)

                return Success({t: self._dependency_tree(t) for t in tgt.dependencies()})

    @staticmethod
    def unresult_tree(tree: Result[Dict[str, Result], Exception]) -> Dict:
        if isinstance(tree, Failure):
            return dict(error=tree)
        else:
            return {k: DependencyResolver.unresult_tree(v) for k, v in tree.unwrap().items()}

    def find_failures(self, tree: Result[Dict[str, Result], Exception]):
        """
        recursively dig into the tree and find all failures
        :param tree:
        :return:
        """

        def dig(t):
            match t:
                case Success(items):
                    return list(chain(*[dig(item) for item in items.values()]))
                case Failure(e):
                    return [e]

        return dig(tree)

    def sorted_dependencies(self, providable: Providable) -> List[Set[str]]:
        match self._to_injected(providable):
            case InjectedByName(name):
                return list(self._dfs(name))
            case tgt:
                from itertools import chain
                visited = set()
                return list(chain(*[self._dfs(d, visited) for d in tgt.dependencies()]))

    # def _provide(self, tgt: str, scope: IScope, trace: list[str] = None):
    #     if trace is None:
    #         trace = []
    #     assert isinstance(tgt, str)
    #     from loguru import logger
    #
    #     try:
    #         deps = [self._provide(d, scope, trace + [d]) for d in self.memoized_deps(tgt)]
    #     except NoMappingError as ke:
    #         logger.error(f"failed to find dependency for {tgt} in {' -> '.join(trace)}")
    #         raise DependencyResolutionError(
    #             f"failed to find dependency for {tgt} in {' -> '.join(trace)}",
    #             [DependencyResolutionFailure(ke.key, trace, ke)]
    #         )
    #
    #     def provider_impl():
    #         provider = self.memoized_provider(tgt)
    #         try:
    #             res = provider(*deps)
    #         except Exception as e:
    #             logger.error(f"failed to provide {tgt} with {deps}.\n {' -> '.join(trace)} \n -> {e}")
    #             raise e
    #         return res
    #
    #     res = scope.provide(tgt, provider_impl, trace)
    #     return res

    def _provide(self, tgt: str, scope: IScope, trace: list[str] = None):
        from collections import deque
        from loguru import logger

        if trace is None:
            trace = []

        assert isinstance(tgt, str)

        # Initialize a stack for dependency resolution
        stack = deque([(tgt, trace, None)])
        results = {}

        while stack:
            current_tgt, current_trace, resolved_deps = stack.pop()

            if current_tgt in results:
                # Dependency already resolved
                continue

            try:
                # If dependencies are not yet resolved, find them
                if resolved_deps is None:
                    deps = self.memoized_deps(current_tgt)
                    unresolved_deps = [d for d in deps if d not in results]

                    if unresolved_deps:
                        # If there are unresolved dependencies, push them onto the stack
                        stack.append((current_tgt, current_trace, None))
                        for dep in unresolved_deps:
                            stack.append((dep, current_trace + [dep], None))
                        continue

                # All dependencies for current_tgt are resolved
                resolved_deps = resolved_deps or [results[d] for d in self.memoized_deps(current_tgt)]

                def provider_impl():
                    provider = self.memoized_provider(current_tgt)
                    try:
                        return provider(*resolved_deps)
                    except Exception as e:
                        bind: IBind = self.helper.total_bindings()[current_tgt]
                        match bind.metadata:
                            case Some(BindMetadata(code_location=Some(ModuleVarLocation(path, line, column)))):
                                location = f"{path}:{line}:{column}"
                            case _:
                                logger.warning(f"failed to retrieve code loc for a binding:{bind}")
                                location = "unknown location"

                        logger.error(
                            f"failed to provide {current_tgt} at {location} from deps:\n{pformat(resolved_deps)}.\n Dependencies: {' -> '.join(current_trace)} \n Exception: {e}")
                        raise e

                # Using scope.provide to get or create the resource
                res = scope.provide(current_tgt, provider_impl, current_trace)
                results[current_tgt] = res

            except NoMappingError as ke:
                logger.error(f"failed to find dependency for {current_tgt} in {' -> '.join(current_trace)}")
                raise DependencyResolutionError(
                    f"failed to find dependency for {current_tgt} in {' -> '.join(current_trace)}",
                    [DependencyResolutionFailure(ke.key, current_trace, ke)]
                )

        return results[tgt]

    def provide(self, providable: Providable, scope: IScope):
        # I need to make this based on Threaded Future rather than asyncio
        # because asyncio does not support creating new loop in a thread
        # which means that we cannot use asyncio.run in a cooruntine
        tgt: Injected = self._to_injected(providable)
        # TODO I want to bind a special key that is only available in this 'provide' scope.
        scope = OverridingScope(scope, overrides=dict(
            __final_target__=tgt,
        ))

        def provide_injected(tgt: Injected, key: str):
            assert isinstance(tgt, Injected), f"tgt must be Injected. got {tgt} of type {type(tgt)}"
            assert isinstance(key, str), f"key must be str. got {key} of type {type(key)}"
            provider = tgt.get_provider()

            # TODO handle the case where this provider raises an exception

            def get_result():
                deps = tgt.dependencies()
                values = [self._provide(d, scope, [key, d]) for d in tgt.dependencies()]
                kwargs = dict(zip(deps, values))
                try:
                    return provider(**kwargs)
                except Exception as e:
                    logger.error(f"failed to provide {key} with {kwargs} \n -> {e}")
                    raise e
                    # raise RuntimeError(f"failed to provide {key} due to an exception!") from e
                # I think we need to give a unique name to this injected so that the value will be cached
                # check if we are in the loop or not

            return scope.provide(key, get_result, trace=[key])

        match tgt:
            case InjectedByName(key):
                res = self._provide(key, scope, trace=[key])
            case EvaledInjected(value, ast) as e:
                of = ast.origin_frame
                assert not isinstance(of, Expr), f"ast.origin_frame must not be Expr. got {of} of type {type(of)}"
                original = ast.origin_frame.filename + ":" + str(ast.origin_frame.lineno)

                key = Path(ast.origin_frame.filename).name + ":L" + str(ast.origin_frame.lineno) + "#" + str(id(tgt))[
                                                                                                         :6]
                # key = f"EvaledInjected#{str(id(tgt))}"
                from loguru import logger
                logger.info(f"naming new key: {key} == {original}")
                res = provide_injected(e, key)
            case InjectedFunction(func, kwargs) as IF if IF.origin_frame is not None:
                frame = IF.origin_frame
                original = frame.filename + ":" + str(frame.lineno)
                key = f"InjectedFunction#{str(id(tgt))}"
                from loguru import logger
                logger.info(f"naming new key: {key} == {original}")
                res = provide_injected(IF, key)
            case DelegatedVar(value, cxt) as dv:
                res = self.provide(dv.eval(), scope)
            case Injected():
                from loguru import logger
                logger.info(f"default injected type:{type(tgt)}")
                provider = tgt.get_provider()
                key = provider.__name__ + "#" + str(id(tgt))
                res = provide_injected(tgt, key)
            case _:
                raise TypeError(f"unhandled providable type:{tgt} with type {type(tgt)}")
        # unless we release the block, the coroutine for the remaining task won't get executed.
        # so we must use async provide where 'session' is used
        # one way to prevent this from happening is to use a thread for each provider.
        return res

    def child(self, session_provider, overrides: 'Design' = None):
        if overrides is None:
            from pinjected import Design,EmptyDesign
            overrides = EmptyDesign()
        from pinjected import providers
        child_design = self.src + providers(
            session=session_provider
        )
        child_resolver = DependencyResolver(child_design)
        return child_resolver


def run_coroutine_in_new_thread(coroutine):
    # Future to store the result of the coroutine
    future = Future()

    # Function to run the coroutine in a new event loop
    def run_coroutine():
        from loguru import logger
        logger.info(f"running coroutine in new thread")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(coroutine)
            future.set_result(result)
        except Exception as e:
            future.set_exception(e)
        finally:
            loop.close()

    # Start the new thread
    t = threading.Thread(target=run_coroutine)
    t.start()
    t.join()

    # Return the result of the coroutine
    return future.result()


@safe
def get_caller_info(level: int):
    caller_frame = inspect.currentframe()
    for _ in range(level):
        caller_frame = caller_frame.f_back
    caller_info = inspect.getframeinfo(caller_frame)
    # caller_info can be None

    file_name = caller_info.filename
    line_number = caller_info.lineno

    return file_name, line_number


def providable_to_injected(tgt: Providable) -> Injected:
    match tgt:
        case str():
            return Injected.by_name(tgt)
        case type():
            return Injected.bind(tgt)
        case Injected():
            return tgt
        case Designed():
            raise TypeError(f"cannot use Designed here, since Designed cannot become an Injected.")
        case DelegatedVar(value, cxt):
            return providable_to_injected(tgt.eval())
        case f if callable(f):
            return Injected.bind(f)
        case _:
            raise TypeError(f"target must be either class or a string or Injected. got {tgt}")


@dataclass
class EventDistributor:
    """
    This class is intended to be a hub for a user to subscribe to events.
    I actually hope use rx.Subjects for this purpose; however, their api changes once a year and I cannot ask user to rely on it.
    Therefore, we just prepare callback system for the user.
    The instance of this class can be retrieved via __pinjected_events__ in the dependency injection.
    """
    callbacks: List[Callable[[...], None]] = field(default_factory=list)
    event_history: list[object] = field(default_factory=list)

    def register(self, callback: Callable[[...], None]):
        self.callbacks.append(callback)
        for event in self.event_history:
            callback(event)

    def unregister(self, callback: Callable[[...], None]):
        self.callbacks.remove(callback)

    def emit(self, event: object):
        self.event_history.append(event)
        for callback in self.callbacks:
            callback(event)


@dataclass
class MyObjectGraph(IObjectGraph):
    _resolver: DependencyResolver
    src_design: "Design"
    scope: IScope
    event_distributor: EventDistributor = field(default_factory=EventDistributor)

    def __post_init__(self):
        assert isinstance(self.resolver, DependencyResolver) or self.resolver is None

    @property
    def resolver(self) -> "DependencyResolver":
        return self._resolver

    @property
    def factory(self) -> IObjectGraphFactory:
        return OGFactoryByDesign(self.src_design)

    @staticmethod
    def root(design: "Design", trace_logger=None) -> "MyObjectGraph":
        distributor = EventDistributor()

        def _trace_logger(event):
            distributor.emit(event)
            if trace_logger is not None:
                trace_logger(event)
            else:
                IScope.default_trace_logger(event)

        scope = MScope(_trace_logger=_trace_logger)
        graph = MyObjectGraph(None, design, scope, distributor)
        design = design.bind_instance(
            session=graph,
            __pinjected_events__=graph.event_distributor,
        )
        resolver = DependencyResolver(design)
        graph._resolver = resolver
        return graph

    def provide(self, target: Providable, level: int = 2):
        """
        :param target:
        :param level: 2 when you are direcly calling. set increased number to show the callee
        :return:
        """
        from loguru import logger
        # I need to get the filename and line number of the caller
        if isinstance(target, Designed):
            return self.child_session(target.design)[target.internal_injected]

        target: Injected = providable_to_injected(target)
        fn, ln = get_caller_info(level).value_or(("unknown_function", "unknown_line"))
        dep_tree = self.resolver.dependency_tree(target)
        dep_tree = DependencyResolver.unresult_tree(dep_tree)
        script = DIGraph(self.design).to_python_script(
            root=target,
            design_path="__dummy__.design",
        )
        logger.debug(f'Pseudo code of the DI graph for ({str(target)[:100]}):\n{script}')
        # logger.debug(f"Pseudo code of the DI graph:")
        # console = Console(stderr=True)
        # script = Syntax(script, "python", theme="ansi_dark", line_numbers=True)
        # console.log(script)
        # rich.print(script)

        failures = self.resolver.find_failures(dep_tree)
        if failures:
            logger.error(f"DI failures: \n{pformat(failures)}")
            raise DependencyResolutionError(f"DI failures: \n{pformat(failures)}", failures)
        res = self.resolver.provide(target, self.scope)
        # flattened = list(chain(*self.resolver.sorted_dependencies(target)))
        # resolved = {k:repr(self.resolver.provide(k))[:100] for k in flattened}
        # logger.debug(f"DI blueprint resolution result:\n{pformat(resolved)}")
        return res

    def child_session(self, overrides: "Design" = None, trace_logger=None):
        if overrides is None:
            from pinjected import Design
            overrides = EmptyDesign
        child_scope = MChildScope(self.scope, set(overrides.keys()),
                                  _trace_logger=trace_logger or self.scope.trace_logger)
        child_graph = MyObjectGraph(None, self.design + overrides, child_scope)
        child_resolver = self.resolver.child(lambda: child_graph, overrides)
        child_graph._resolver = child_resolver
        return child_graph

    @property
    def design(self):
        return self.src_design

    @property
    def design_with_implicits(self):
        from pinjected import providers
        return providers(**DIGraphHelper(self.design).total_mappings()).unbind('session')

    def __repr__(self):
        return f"MyObjectGraph({self.design})"

    def auto_sync(self, rejector=None):
        return AutoSyncGraph(self, rejector)


@dataclass
class AutoSyncGraph:
    src: IObjectGraph
    rejector: Callable[[Any], bool] = field(default=None)
    """
    if rejector returns true for an item, it will not be awaited
    """

    def __post_init__(self):
        if self.rejector is None:
            self.rejector = lambda x: False

    def __getitem__(self, item):
        item = self.src[item]
        if not self.rejector(item) and inspect.isawaitable(item):
            async def waiter():
                return await item

            # I need to distinguish if it's Var or not...

            return asyncio.run(waiter())
        return item


def sessioned_value_proxy_context(parent: IObjectGraph, session: IObjectGraph):
    from pinjected.di.dynamic_proxy import DynamicProxyContextImpl
    return DynamicProxyContextImpl(
        lambda a: a.value,
        lambda x: SessionValue(
            parent,
            Designed.bind(Injected.pure(x)),
            session
        ),
        "SessionValueProxy"
    )


@dataclass
class SessionValue(Generic[T]):
    """a class that holds a lazy value and the session used for producing the value.
    how can I access session of DelegatedVar[SessionValue]?
    current implementatoin uses accessor to get value and then bypassess getattr for this value.
    so I need to tell the context which vars are supposed to be accessed through DelegatedVar
    actually, we can access session through delegatedvar.value.session.
    since value shows the internal value, while eval() returns the final semantic value.
    """
    parent: IObjectGraph
    designed: Designed[T]
    session: IObjectGraph = field(default=None)
    _cache: Maybe[T] = field(default=Nothing)

    def __post_init__(self):
        if self.session is None:
            self.session = self.parent.child_session(self.designed.design)

    @property
    def value(self) -> Any:
        if self._cache is Nothing:
            self._cache = Some(self.session[self.designed.internal_injected])
        return self._cache.unwrap()
