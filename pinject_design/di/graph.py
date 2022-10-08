import inspect
from dataclasses import dataclass, field
from types import FunctionType
from typing import Union, Type, Callable, TypeVar, List, Any, Generic

from loguru import logger
from makefun import create_function
from pinject import binding_keys, locations, SINGLETON
from pinject.bindings import default_get_arg_names_from_class_name, BindingMapping, new_binding_to_instance
from pinject.errors import NothingInjectableForArgError
from pinject.object_graph import ObjectGraph
from pinject.object_providers import ObjectProvider
from returns.maybe import Nothing, Maybe, Some

from pinject_design.di.designed import Designed
from pinject_design.di.injected import Injected
from pinject_design.di.proxiable import DelegatedVar
from pinject_design.di.session import OverridenBindableScopes
from pinject_design.exceptions import DependencyResolutionFailure

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


class ExtendedObjectGraph:
    """
    an object graph which can also provide instances based on its name not only from class object.
    """

    def __init__(self, design: "Design", src: ObjectGraph):
        self.design = design
        # TODO override ObjectGraph vars to have 'session' as special name to be injected.
        # TODO use new_binding_to_instance to bind self as session
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
        :param target:
        :return:
        """
        from pinject_design.di.static_proxy import Expr
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
                assert not isinstance(target,DelegatedVar),str(target)
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

    def provide(self, target: Providable) -> Union[object, T]:
        try:
            return self._provide(target)
        except NothingInjectableForArgError as e:
            missings = self._inspect_dependencies(target)
            if missings:
                for missing in missings:
                    logger.error(f"failed to find dependency:{missing}")
                raise MissingDependencyException.create(missings)
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

    def sessioned(self, target: Providable) -> "DelegatedVar[Union[object,T]]":
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
                from pinject_design.di.proxiable import DelegatedVar
                return DelegatedVar(val, ctx)
            case _:
                raise TypeError(f"Unknown target:{target} queried for DI.")

    def run(self, f):
        argspec = inspect.getfullargspec(f)
        assert "self" not in argspec.args, f"self in {argspec.args}, of {f}"
        # logger.info(self)
        assert argspec.varargs is None
        kwargs = {k: self.provide(k) for k in argspec.args}
        return f(**kwargs)

    def __repr__(self):
        return f"ExtendedObjectGraph({self.design})"

    def __getitem__(self, item):
        return self.provide(item)

    def child_session(self, overrides: "Design" = None) -> "ChildGraph":
        """
        1, make binding_keys from design
        2. make a scope
        3.
        :param overrides:
        :return:
        """
        return ChildGraph(self.src, self.design, overrides)


def sessioned_value_proxy_context(parent: ExtendedObjectGraph, session: ExtendedObjectGraph):
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


@dataclass
class SessionValue(Generic[T]):
    """a class that holds a lazy value and the session used for producing the value.
    I want to make use of this to act as a proxy.
    How can I make many proxy variables?
    we can map and zip on this variable.
    and also, I want to yield from this variable.
    which should yield SessionValue too.
    """
    parent: ExtendedObjectGraph
    designed: Designed[T]
    session: ExtendedObjectGraph = field(default=None)
    _cache: Maybe[T] = field(default=Nothing)

    def __post_init__(self):
        if self.session is None:
            self.session = self.parent.child_session(self.designed.design)

    @property
    def value(self) -> Any:
        if self._cache is Nothing:
            self._cache = Some(self.session[self.designed.internal_injected])
        return self._cache.unwrap()
