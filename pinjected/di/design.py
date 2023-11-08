import inspect
from copy import copy
from dataclasses import dataclass, field, replace
from functools import wraps
from itertools import chain
from typing import TypeVar, List, Dict, Union, Callable, Type

from cytoolz import merge
from makefun import create_function
from returns.maybe import Some

from pinjected.di.injected import Injected
from pinjected.di.bindings import Bind, InjectedBind, BindMetadata
from pinjected.di.graph import IObjectGraph, MyObjectGraph

from pinjected.di.injected import extract_dependency_including_self, InjectedPure, InjectedFunction
from pinjected.di.proxiable import DelegatedVar
# from pinjected.di.util import get_class_aware_args, get_dict_diff, check_picklable
from pinjected.di.monadic import getitem_opt
from pinjected.graph_inspection import DIGraphHelper

T = TypeVar("T")
U = TypeVar("U")


def map_wrap(src, f):
    @wraps(src)
    def wrapper(*args, **kwargs):
        return f(src(*args, **kwargs))

    wrapper.__signature__ = inspect.signature(src)
    return wrapper


def remove_kwargs_from_func(f, kwargs: List[str]):
    deps = extract_dependency_including_self(f)
    to_remove = set(kwargs)
    new_kwargs = deps - to_remove
    func_name = f.__name__.replace("<lambda>", "_lambda_")
    sig = f"""{func_name}({",".join(new_kwargs)})"""

    def impl(**called_kwargs):
        deleted = deps & to_remove
        # for self, you must check whether f is method or not
        if inspect.ismethod(f):
            deleted = deleted - {"self"}
        d_kwargs = {k: None for k in deleted}
        return f(**called_kwargs, **d_kwargs)

    return create_function(sig, impl)


@dataclass
class Design:
    """
    The ``Design`` class acts as a central registry for managing and applying dependency injection
    within your application. It allows for the binding of various components, instances, and providers,
    enabling a cohesive and flexible way to handle dependencies. The class is integral in constructing
    applications that adhere to the Dependency Inversion Principle, fostering a decoupled and easily
    maintainable codebase.

    Basic Usage:
    ------------

    **Adding Bindings:**

    The ``Design`` class allows for the binding of instances, providers, and classes.
    Each type of binding adds different kinds of objects to the design, contributing
    to the overall dependency structure.

    .. code-block:: python

        from pinjected import Design
        from dataclasses import dataclass

        @dataclass
        class DepObject:
            a: int
            b: int
            c: int
            d: int

        @dataclass
        class App:
            dep: DepObject

            def run(self):
                print(self.dep.a + self.dep.b + self.dep.c + self.dep.d)

        d = Design().bind_instance(
            a=0,
            b=1
        ).bind_provider(
            c=lambda a, b: a + b,
            d=lambda a, b, c: a + b + c
        ).bind_class(
            dep=DepObject
        )

        # The `to_graph` method compiles the bindings into a graph structure, which can then provide
        # the necessary components for your application.
        d.to_graph().provide(App).run()

    Advanced Usage:
    ---------------

    **Combining Multiple Designs:**

    In more complex scenarios, you might need to combine multiple ``Design`` instances.
    This could be necessary if different modules or components of your application require
    different dependency configurations. The ``Design`` class supports the combination of instances,
    allowing for the overlaying and overriding of bindings.

    .. code-block:: python

        d1 = Design().bind_instance(
            a=0
        )
        d2 = Design().bind_instance(
            b=1
        )
        d3 = Design().bind_instance(
            b=0
        )

        # The `+` operator combines designs. If the same binding exists in both designs,
        # the one from the rightmost design (latest) will take precedence.
        assert (d1 + d2).provide("b") == 1  # 'b' from d2 takes precedence
        assert (d1 + d2 + d3).provide("b") == 0  # 'b' from d3 overrides the others

    This feature ensures that ``Design`` instances are composable and adaptable, providing
    a robust foundation for building complex, modular applications with dependency injection.
    """
    bindings: Dict[str, Bind] = field(default_factory=dict)
    multi_binds: dict = field(default_factory=dict)
    modules: list = field(default_factory=list)
    classes: list = field(default_factory=list)

    def __getstate__(self):
        res = dict(
            bindings=self.bindings,
            multi_binds=self.multi_binds,
            modules=[m.__name__ for m in self.modules],
            classes=self.classes,
        )
        return res

    def __setstate__(self, state):
        mods = state["modules"]
        import importlib
        mods = [importlib.import_module(
            name=m
        ) for m in mods]
        state["modules"] = mods
        for k, v in state.items():
            setattr(self, k, v)

    def __add__(self, other: Union["Design", Dict[str, Bind]]):
        other = self._ensure_dbc(other)
        return self.merged(other)

    def bind(self, key: str) -> "DesignBindContext":

        return DesignBindContext(self, key)

    def _ensure_dbc(self, other: Union["Design", Dict[str, Bind]]):
        match other:
            case Design():
                return other
            case dict() if all([isinstance(v, Bind) for v in other.values()]):
                return Design(other)
            case _:
                raise ValueError(f"cannot add {type(other)} to Design")

    def _merge_multi_binds(self, src, dst):
        keys = src.keys() | dst.keys()
        multi = {k: (
                getitem_opt(src, k).value_or([]) +
                getitem_opt(dst, k).value_or([])
        ) for k in keys}
        return multi

    def merged(self, other: "Design"):
        """creates another instance with merged bindings. does not modify self"""
        # logger.debug(f"merging:\n\t{self} to \n\t{other}")
        assert isinstance(other, Design), f"merge target is not a Design. type:{type(other)}:{other}"

        res = Design(
            bindings=merge(self.bindings, other.bindings),
            multi_binds=self._merge_multi_binds(self.multi_binds, other.multi_binds),
            modules=list(set(self.modules) | set(other.modules)),
            classes=list(set(self.classes) | set(other.classes)),
        )
        return res

    def bind_instance(self, **kwargs, ):
        """
        Here, I need to find the CodeLocation for each binding.
        :param kwargs:
        :param __binding_metadata__: a dict of [str,BindMetadata]
        :return:
        """
        x = self
        for k, v in kwargs.items():
            if isinstance(v, type):
                from loguru import logger
                logger.warning(f"{k} is bound to class {v} with 'bind_instance' do you mean 'bind_class'?")
            x += Design({k: InjectedBind(InjectedPure(v))})
        return x

    def bind_provider(self, **kwargs: Union[Callable, Injected]):
        x = self
        for k, v in kwargs.items():
            # logger.info(f"binding provider:{k}=>{v}")
            def parse(item):
                from loguru import logger
                match item:
                    case type():
                        logger.warning(f"{k}->{v}: class is used for bind_provider. fixing automatically.")
                        return x.bind(k).to_class(item)
                    case Injected():
                        return x.bind(k).to_provider(item)
                    case DelegatedVar():
                        return parse(item.eval())
                    case non_func if not callable(non_func):
                        logger.warning(
                            f"{k}->{item}: non-callable or non-injected is passed to bind_provider. fixing automatically.")
                        return x.bind(k).to_instance(v)
                    case _:
                        return x.bind(k).to_provider(item)

            x = parse(v)
        return x

    def bind_class(self, **kwargs):
        from loguru import logger
        x = self
        for k, v in kwargs.items():
            if isinstance(v, Injected):
                logger.warning(f"{k}->{v}: Injected instance is used for bind_class. fixing automatically.")
                x = x.bind(k).to_provider(v)
            else:
                x = x.bind(k).to_class(v)
        return x

    def add_metadata(self, **kwargs: "BindMetadata") -> "Design":
        res = self
        for k, meta in kwargs.items():
            res += Design(
                bindings={k: InjectedBind(self[k].to_injected(), metadata=Some(meta))}
            )
        return res

    def to_graph(self, modules=None, classes=None, trace_logger=None) -> IObjectGraph:
        # So MyObjectGraph's session is still corrupt?
        # TODO add special variables to monitor the state of this provider.
        # __pinjected_events__ <= subject of events that are emitted by pinjected
        # but I don't want to depend on rx, right?
        design = self + Design(
            modules=modules or [],
            classes=classes or []
        )
        return MyObjectGraph.root(design, trace_logger=trace_logger)

    def run(self, f, modules=None, classes=None):
        return self.to_graph(modules, classes).run(f)

    def provide(self, target: Union[str, Type[T]], modules=None, classes=None, trace_logger=None) -> T:
        """
        :param target: provided name
        :param modules: modules to use for graph construction
        :return:
        """
        return self.to_graph(modules=modules, classes=classes, trace_logger=trace_logger).provide(target, level=4)

    def copy(self):
        return self.__class__(
            bindings=self.bindings.copy(),
            multi_binds=copy(self.multi_binds),
            modules=copy(self.modules),
            classes=copy(self.classes),
        )

    def map_value(self, src_key, f):
        """
        :param src_key:
        :param f:
        :return: Design
        """
        mapped_binding = self.bindings[src_key].map(f)
        return self + Design({src_key: mapped_binding})

    def apply_injected_func(self, key: str, injected_func: Injected[Callable]):
        bind = self.bindings[key]
        applied_bind = InjectedBind(
            bind.to_injected().apply_injected_function(injected_func),
        )
        return self + Design({key: applied_bind})

    def keys(self):
        return self.bindings.keys()

    def unbind(self, key) -> "Design":
        if key in self.bindings:
            copied = self.bindings.copy()
            del copied[key]
            return replace(self,
                           bindings=copied
                           )
        return self

    def __contains__(self, item):
        return item in self.bindings

    def __getitem__(self, item):
        return self.bindings[item]

    def __str__(self):
        return f"Design(len={len(self.bindings) + len(self.multi_binds)})"

    def __repr__(self):
        return str(self)

    def table_str(self):
        import tabulate
        binds = tabulate.tabulate(sorted(list(self.bindings.items())))
        multis = tabulate.tabulate(sorted(list(self.multi_binds.items())))
        return binds + "\n" + multis

    def to_str_dict(self):
        res = dict()
        for k, v in self.bindings.items():
            match v:
                case InjectedBind(InjectedFunction(f, args)):
                    res[k] = f.__name__
                case InjectedBind(InjectedPure(value)):
                    res[k] = str(value)
                case any:
                    res[k] = str(any)
        return res

    def build(self):
        design = self
        for k, providers in self.multi_binds.items():
            # assert k not in self.bindings,f"multi binding key overwrapping with normal binding key,{k}"
            if len(providers) == 0:
                design = design.bind_instance(**{k: set()})
            else:
                design = self._add_multi_binding(design, k, providers)
        return design

    def _ensure_provider_name(self, k, method):
        """set appropriate name for provider function to be recognized by pinject"""
        name = f"provide_{k}"
        if not method.__name__ == name:
            # there are cases where you cannot directly set __name__ attribute.
            # and sometimes pinject.inject decorator is already applied so wrapping that again is not appropriate
            # so, the solution is to first try setting __name__ and then try wrapping if failed.
            try:
                method.__name__ = name
                return method
            except AttributeError as ae:
                from loguru import logger
                logger.warning(f"somehow failed to assign new name to a provider function. trying to wrap.")

                def _wrapper(self, *args, **kwargs):
                    return method(*args, **kwargs)

                _wrapper.__name__ = name
                _wrapper.__signature__ = inspect.signature(method)
                return _wrapper
        return method

    def multi_bind_provider(self, **kwargs):
        """:cvar adds a provider to specified key so that result of calling multiple providers will be
        aggregated and provided as a list.
        """

        return self + Design(
            multi_binds={
                k: [v]
                for k, v in kwargs.items()
            }
        )

    def multi_bind_empty(self, *keys):
        """:key returns a new design which returns a [] for "key" as default value. """
        # None works as a signal to remove
        return self + Design(
            multi_binds={
                k: [None] for k in keys
            }
        )

    def _acc_multi_provider(self, providers):
        res = []
        for p in providers:
            if p is None:  # this is set by empty_multi_provider call
                res = []
            else:
                res.append(p)
        return res

    def _add_multi_binding(self, design, k, providers: list):
        from pinjected.di.util import get_class_aware_args
        # TODO use Injected's mzip.
        providers = self._acc_multi_provider(providers)
        deps = [f.dependencies() if isinstance(f, Injected) else get_class_aware_args(f) for f in providers]
        dep_set = set(chain(*deps))
        if "self" in dep_set:
            dep_set.remove("self")
        f_signature = f"multi_bind_provider_{k}({','.join(dep_set)})"
        # logger.info(f_signature)
        for ds in deps:
            for d in ds:
                assert d in dep_set

        def create_impl(tgt_providers, tgt_dependencies):
            def f_impl(**kwargs):
                # from loguru import logger

                # logger.info(f"{f_signature} called with {list(kwargs.keys())}")
                values = []
                for provider, ds in zip(tgt_providers, tgt_dependencies):
                    p_deps = {k: kwargs[k] for k in ds}
                    v = provider(**p_deps)
                    values.append(v)  # unhashable type...
                return values

            return f_impl

        new_f = create_function(f_signature, create_impl(providers, deps))
        binding = {k: new_f}
        # logger.info(binding)
        design = design.bind_provider(**binding)
        return design

    def diff(self, other):
        from pinjected.di.util import get_dict_diff
        d = get_dict_diff(self.bindings, other.bindings)
        return d

    def inspect_picklability(self):
        from pinjected.di.util import check_picklable
        from loguru import logger
        logger.info(f"checking picklability of bindings")
        check_picklable(self.bindings)
        logger.info(f"checking picklability of multi-binds")
        check_picklable(self.multi_binds)
        logger.info(f"checking picklability of modules")
        check_picklable(self.modules)
        logger.info(f"checking picklability of classes")
        check_picklable(self.classes)

    def add_modules(self, *modules):
        return self + Design(modules=list(modules))

    def add_classes(self, *classes):
        return self + Design(classes=list(classes))

    def to_vis_graph(self) -> "DIGraph":
        from pinjected.visualize_di import DIGraph
        return DIGraph(self)

    def purify(self, target: "Providable"):
        """
        given an injected, returns a minimized design which can provide the target.
        :param target:
        :return:
        """
        # ah sometimes the deps require 'session'
        # and we don't know if the session has enough bindings to provide the target.

        return self.to_graph().resolver.purified_design(target).unbind('session')


class DesignBindContext:
    def __init__(self, src: "Design", key: str):
        self.src = src
        self.key = key

    def to_class(self, cls: type):
        assert isinstance(cls, type), f"binding must be a class! got:{cls} for key:{self.src}"
        return self.src + Design({self.key: InjectedBind(Injected.bind(cls))})

    def to_instance(self, instance):
        return self.src + Design({self.key: InjectedBind(Injected.pure(instance))})

    def to_provider(self, provider):
        if isinstance(provider, Injected):
            return self.src + Design({self.key: InjectedBind(provider)})
        else:
            return self.src + Design({self.key: InjectedBind(Injected.bind(provider))})
