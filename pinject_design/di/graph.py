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
from typing import Union, Type, Callable, TypeVar, List, Any, Generic, Awaitable, Set, Dict

import yaml
from makefun import create_function
from pinject import binding_keys, locations, SINGLETON
from pinject.bindings import default_get_arg_names_from_class_name, BindingMapping, new_binding_to_instance
from pinject.errors import NothingInjectableForArgError, OnlyInstantiableViaProviderFunctionError
from pinject.object_graph import ObjectGraph
from pinject.object_providers import ObjectProvider
from returns.maybe import Nothing, Maybe, Some
from returns.result import safe, Result, Failure, Success

from pinject_design.di.app_injected import EvaledInjected
from pinject_design.di.ast import Expr
# from pinject_design import Design
from pinject_design.di.designed import Designed
from pinject_design.di.injected import Injected, InjectedByName, InjectedFunction
from pinject_design.di.proxiable import DelegatedVar
from pinject_design.di.session import OverridenBindableScopes, SessionScope, ISessionScope
from pinject_design.di.sessioned import Sessioned
from pinject_design.exceptions import DependencyResolutionFailure, DependencyResolutionError
from pinject_design.graph_inspection import DIGraphHelper

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


Providable = Union[str, Type[T], Injected[T], Callable, Designed[T], DelegatedVar[Injected], DelegatedVar[Designed]]


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
        from pinject_design.di.sessioned import sessioned_ast_context
        designed = self._providable_to_designed(providable)
        item = Sessioned(self, designed)
        ctx = sessioned_ast_context(self)
        from pinject_design.di.ast import Object
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


# using async was not a good Idea since all the function needs to be assumed a coroutine.
# we don't assume the provider function is a coroutine.

class IScope:
    @abstractmethod
    def provide(self, key, provider_func: Callable[[], Any], trace: List) -> Any:
        pass

    @abstractmethod
    def __contains__(self, item):
        raise NotImplementedError()


def trace_string(trace: list[str]):
    # res = "\n"
    # for i, item in enumerate(trace):
    #     res += f"{i * '  '}{item} -> \n"
    # return res
    return f" -> ".join(trace)


@dataclass
class MScope(IScope):
    cache: dict[str, Any] = field(default_factory=dict)

    def __getstate__(self):
        raise NotImplementedError("MScope is not serializable")

    def provide(self, key, provider: Callable[[], Any], trace: List) -> Any:
        from loguru import logger
        # with self.lock:
        if key in self.cache:
            return self.cache[key]
        assert isinstance(trace, list) and all(isinstance(item, str) for item in trace)
        logger.info(trace_string(trace))
        res = provider()
        self.cache[key] = res
        res = self.cache[key]
        logger.info(f"{' <- '.join(trace)} = {repr(res)[:100]}")
        #
        return self.cache[key]

    def __contains__(self, item):
        return item in self.cache


@dataclass
class MChildScope(IScope):
    parent: IScope
    override_targets: set
    cache: dict[str, Any] = field(default_factory=dict)

    def __getstate__(self):
        raise NotImplementedError("MChildScope is not serializable")

    def provide(self, key, provider_func: Callable[[], Any], trace: List) -> Any:
        from loguru import logger
        if key not in self.cache:
            if key in self.override_targets or key not in self.parent:
                logger.info(f"providing from child:{' -> '.join(trace)}")
                res = provider_func()
                self.cache[key] = res
                res = self.cache[key]
                logger.info(f"provided from child: {' <- '.join(trace)} = {str(res)[:100]}")
            else:
                self.cache[key] = self.parent.provide(key, provider_func, trace)
        return self.cache[key]

    def __contains__(self, item):
        return item in self.cache or item in self.parent


@dataclass
class DependencyResolver:
    """
    okey I want to make a variant that uses IMPLICIT_BINDINGS when the target is not in the mapping.
    what we need is actually a str->Injected mapping.
    """
    src: "Design"

    def _to_injected(self, tgt: Providable):
        match tgt:
            case str():
                return Injected.by_name(tgt)
            case type():
                return Injected.bind(tgt)
            case Injected():
                return tgt
            case DelegatedVar(value, cxt):
                return self._to_injected(tgt.eval())
            case f if callable(f):
                return Injected.bind(f)
            case _:
                raise TypeError(f"target must be either class or a string or Injected. got {tgt}")

    def __post_init__(self):
        # gather things to build providers graph
        helper = DIGraphHelper(self.src)
        #
        self.mapping: dict[str, Injected] = helper.total_mappings()

        @lru_cache()
        def _memoized_provider(tgt: str):
            return self.mapping[tgt].get_provider()

        self.memoized_provider = _memoized_provider

        @lru_cache()
        def _memoized_deps(tgt: str):
            if tgt not in self.mapping:
                raise KeyError(f"target {tgt} is not in the dependency injection mapping.")
            return self.mapping[tgt].dependencies()

        self.memoized_deps = _memoized_deps

    def _dfs(self, tgt: str, visited: set[str] = None):
        if visited is None:
            visited = set()
        if tgt in visited:
            return
        visited.add(tgt)
        deps = self.memoized_deps(tgt)
        yield tgt
        for dep in deps:
            yield from self._dfs(dep, visited)

    def _dependency_tree(self, tgt: str, trace: list[str] = None) -> Result[Dict[str, Result], Exception]:
        trace = trace or [tgt]
        try:
            res = dict()
            deps = self.memoized_deps(tgt)
            for d in deps:
                assert d not in trace, f"cycle detected: {d} is requested in {' -> '.join(trace)}"
                res[d] = self._dependency_tree(d, trace + [d])
            return Success(res)
        except KeyError as ke:
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
    def unresult_tree(tree:Result[Dict[str, Result], Exception])->Dict:
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

    def _provide(self, tgt: str, scope: IScope, trace: list[str] = None):
        if trace is None:
            trace = []
        assert isinstance(tgt, str)
        from loguru import logger
        deps = [self._provide(d, scope, trace + [d]) for d in self.memoized_deps(tgt)]

        def provider_impl():
            provider = self.memoized_provider(tgt)
            try:
                res = provider(*deps)
            except Exception as e:
                logger.error(f"failed to provide {tgt} with {deps}.\n {' -> '.join(trace)} \n -> {e}")
                raise e
            return res

        res = scope.provide(tgt, provider_impl, trace)
        return res

    def provide(self, providable: Providable, scope: IScope):
        # I need to make this based on Threaded Future rather than asyncio
        # because asyncio does not support creating new loop in a thread
        # which means that we cannot use asyncio.run in a cooruntine
        tgt: Injected = self._to_injected(providable)

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
                    #raise RuntimeError(f"failed to provide {key} due to an exception!") from e
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

                key = Path(ast.origin_frame.filename).name + ":" + str(ast.origin_frame.lineno) + "#" + str(id(tgt))
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
            from pinject_design import Design
            overrides = Design()
        child_design = self.src + overrides.bind_provider(session=session_provider)
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


@dataclass
class MyObjectGraph(IObjectGraph):
    resolver: DependencyResolver
    src_design: "Design"
    scope: IScope

    def __post_init__(self):
        assert isinstance(self.resolver, DependencyResolver) or self.resolver is None

    @property
    def factory(self) -> IObjectGraphFactory:
        return OGFactoryByDesign(self.src_design)

    @staticmethod
    def root(design: "Design") -> "MyObjectGraph":
        scope = MScope()
        graph = MyObjectGraph(None, design, scope)
        design = design.bind_instance(session=graph)
        resolver = DependencyResolver(design)
        graph.resolver = resolver
        return graph

    def provide(self, target: Providable, level: int = 2):
        """
        :param target:
        :param level: 2 when you are direcly calling. set increased number to show the callee
        :return:
        """
        from loguru import logger
        # I need to get the filename and line number of the caller

        fn, ln = get_caller_info(level).value_or(("unknown_function", "unknown_line"))
        dep_tree = self.resolver.dependency_tree(target)
        dep_tree = DependencyResolver.unresult_tree(dep_tree)
        logger.debug(
            f"{fn}:{ln} => DI blueprint for {str(target)[:100]}:\n{yaml.dump(dep_tree)}")
        failures = self.resolver.find_failures(dep_tree)
        if failures:
            logger.error(f"DI failures: \n{pformat(failures)}")
            raise DependencyResolutionError(f"DI failures: \n{pformat(failures)}", failures)
        res = self.resolver.provide(target, self.scope)
        # flattened = list(chain(*self.resolver.sorted_dependencies(target)))
        # resolved = {k:repr(self.resolver.provide(k))[:100] for k in flattened}
        # logger.debug(f"DI blueprint resolution result:\n{pformat(resolved)}")
        return res

    def child_session(self, overrides: "Design" = None):
        if overrides is None:
            from pinject_design import Design
            overrides = Design()
        child_scope = MChildScope(self.scope, set(overrides.keys()))
        child_graph = MyObjectGraph(None, self.design + overrides, child_scope)
        child_resolver = self.resolver.child(lambda: child_graph, overrides)
        child_graph.resolver = child_resolver
        return child_graph

    @property
    def design(self):
        return self.src_design


class ExtendedObjectGraph(IObjectGraph):
    """
    an object graph which can also provide instances based on its name not only from class object.
    TODO I need to change the implementation to not to use pinject, so that I can provide async providers
    """

    @property
    def design(self):
        return self._design

    def __init__(self, design: "Design", src: ObjectGraph):
        self._design = design
        back_frame = locations.get_back_frame_loc()
        session_binding = new_binding_to_instance(
            binding_keys.new("session"),
            to_instance=self,
            in_scope=SINGLETON,
            get_binding_loc_fn=lambda: back_frame
        )
        src._obj_provider._binding_mapping._binding_key_to_binding.update(
            {session_binding.binding_key: session_binding}
        )
        self.src = src

    def _provide(self, target: Providable) -> Union[object, T]:
        """
        Hacks pinject to provide from string. by creating a new class.
        :param targe
        :return:
        """
        match target:
            case str():
                return self._provide(Injected.by_name(target))
            case type():
                return self.src.provide(target)
            case Injected():
                return self._provide_injected(target)
            case Designed():
                return self.child_session(target.design)[target.internal_injected]
            case DelegatedVar():
                return self._provide(target.eval())
            case _ if callable(target):
                assert not isinstance(target, DelegatedVar), str(target)
                return self.run(target)
            case _:
                raise TypeError(f"target must be either class or a string or Injected. got {target}")

    def _provide_injected(self, injected: Injected[T]) -> T:
        deps = injected.dependencies()
        if 'self' in deps:
            deps.remove('self')
        signature = f"""__init__(self,{','.join(deps)})"""

        def impl(self, **kwargs):
            self.data = injected.get_provider()(**kwargs)

        __init__ = create_function(signature, func_impl=impl)
        Request = type("Request", (object,), dict(__init__=__init__))
        return self.src.provide(Request).data

    def provide(self, target: Providable, level: int) -> Union[object, T]:
        try:
            return self._provide(target)
        except NothingInjectableForArgError as e:
            missings = self._inspect_dependencies(target)
            if missings:
                for missing in missings:
                    from loguru import logger
                    logger.error(f"failed to find dependency:{missing}")
                raise MissingDependencyException.create(missings)
            raise e
        except OnlyInstantiableViaProviderFunctionError as e:
            from loguru import logger
            logger.error(f"failed to provide target:{target}.")
            logger.error(f"probably caused by errors inside provider function implementations.")
            logger.error(f"context:{e.__context__}")
            # TODO I feel like I should implement the DI by myself rather than using pinject.
            raise e
        except Exception as e:
            from loguru import logger
            import traceback
            trace = traceback.format_exc()
            logger.error(f"failed to provide target:{target} due to {e}. Traceback:{trace}")
            raise e

    def _inspect_dependencies(self, target: Providable):
        # preventing circular import
        from pinject_design.visualize_di import DIGraph
        deps, design = self._extract_dependencies(target)
        missings = DIGraph(design).find_missing_dependencies(deps)
        return missings

    def _extract_dependencies(self, target: Providable):
        match target:
            case type():
                deps = [default_get_arg_names_from_class_name(target.__name__)[0]]
                from pinject_design import Design
                return deps, self.design + Design(classes=[target])
            case Injected():
                return target.dependencies(), self.design
            case str():
                return [target], self.design
            case Designed():
                deps, d = self._extract_dependencies(target.internal_injected)
                return deps, d + target.design
            case DelegatedVar():
                return self._extract_dependencies(target.eval())
            case x if callable(x):
                return self._extract_dependencies(Injected.bind(x))
            case other:
                raise TypeError(f"cannot extract dependencies. unsupported :{target}")

    def __repr__(self):
        return f"ExtendedObjectGraph({self.design})"

    def child_session(self, overrides: "Design" = None) -> "ChildGraph":
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
        return ChildGraph(self.src, self.design, overrides)


def sessioned_value_proxy_context(parent: IObjectGraph, session: IObjectGraph):
    from pinject_design.di.dynamic_proxy import DynamicProxyContextImpl
    return DynamicProxyContextImpl(
        lambda a: a.value,
        lambda x: SessionValue(
            parent,
            Designed.bind(Injected.pure(x)),
            session
        ),
        "SessionValueProxy"
    )


def _merged_binding_mapping(src_graph: ObjectGraph, child_graph: ObjectGraph):
    src: BindingMapping = src_graph._obj_provider._binding_mapping
    child: BindingMapping = child_graph._obj_provider._binding_mapping
    return BindingMapping(
        {**src._binding_key_to_binding, **child._binding_key_to_binding},
        {**src._collided_binding_key_to_bindings, **child._collided_binding_key_to_bindings}
    )


class ChildGraph(ExtendedObjectGraph):
    def __init__(self, src: ObjectGraph, design: "Design", overrides: "Design" = None):
        """
        :param src:
        :param design:
        :param overrides: an overriding design to provide for creating new graph.
        """
        if overrides is None:
            from pinject_design import Design
            overrides = Design()
            # binding_mapping:BindingMapping = design_to_binding_keys(overrides)
        child_graph = overrides.to_graph().src
        override_keys = set(child_graph._obj_provider._binding_mapping._binding_key_to_binding.keys())
        new_mapping = _merged_binding_mapping(src, child_graph)
        new_scopes = OverridenBindableScopes(src._obj_provider._bindable_scopes, override_keys)
        # now we need overriden child scope
        child_obj_provider = ObjectProvider(
            binding_mapping=new_mapping,
            bindable_scopes=new_scopes,
            allow_injecting_none=src._obj_provider._allow_injecting_none
        )
        child_obj_graph = ObjectGraph(
            obj_provider=child_obj_provider,
            injection_context_factory=src._injection_context_factory,
            is_injectable_fn=src._is_injectable_fn,
            use_short_stack_traces=src._use_short_stack_traces
        )
        super().__init__(
            design + overrides,
            child_obj_graph,
        )
        self.overrides = overrides
        self.scopes = new_scopes


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
