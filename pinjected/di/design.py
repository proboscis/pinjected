import inspect
from copy import copy
from dataclasses import dataclass, field, replace
from functools import wraps
from typing import TypeVar, List, Dict, Union, Callable, Type, Self

from cytoolz import merge
from makefun import create_function

from pinjected.di.graph import DependencyResolver
from pinjected.di.implicit_globals import IMPLICIT_BINDINGS
from pinjected.di.injected import Injected
from pinjected.di.injected import extract_dependency_including_self, InjectedPure, InjectedFunction
# from pinjected.di.util import get_class_aware_args, get_dict_diff, check_picklable
from pinjected.di.proxiable import DelegatedVar
from pinjected.v2.binds import IBind, BindInjected
from pinjected.v2.keys import IBindKey, StrBindKey

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
    bindings: Dict[IBindKey, IBind] = field(default_factory=dict)
    modules: list = field(default_factory=list)

    def __getstate__(self):
        res = dict(
            bindings=self.bindings,
            modules=[m.__name__ for m in self.modules],
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

    def __add__(self, other: "Design"):
        assert isinstance(other, Design), f"cannot add {type(other)} to Design"
        res = Design(
            bindings=merge(self.bindings, other.bindings),
            modules=list(set(self.modules) | set(other.modules)),
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
            x += Design({StrBindKey(k): BindInjected(Injected.pure(v))})
        return x

    def bind_provider(self, **kwargs: Union[Callable, Injected]):
        bindings = dict()
        for k, v in kwargs.items():
            # logger.info(f"binding provider:{k}=>{v}")
            from loguru import logger
            match v:
                case type():
                    #logger.warning(f"{k}->{v}: class is used for bind_provider. fixing automatically.")
                    bindings[StrBindKey(k)] = BindInjected(Injected.bind(v))
                case Injected():
                    bindings[StrBindKey(k)] = BindInjected(v)
                case DelegatedVar():
                    bindings[StrBindKey(k)] = BindInjected(v.eval())
                case non_func if not callable(non_func):
                    logger.warning(
                        f"{k}->{v}: non-callable or non-injected is passed to bind_provider. fixing automatically.")
                    bindings[StrBindKey(k)] = BindInjected(Injected.pure(v))
                case func if callable(func):
                    bindings[StrBindKey(k)] = BindInjected(Injected.bind(func))
                case _:
                    raise ValueError(f"cannot bind {k} to {v}")

        return self + Design(
            bindings=bindings,
        )

    def add_metadata(self, **kwargs: "BindMetadata") -> "Design":
        res = self
        for k, meta in kwargs.items():
            key = StrBindKey(k)
            bind: IBind = self.bindings[key]
            res += Design(
                bindings={key: bind.update_metadata(meta)}
            )
        return res

    def to_resolver(self):
        from pinjected.v2.resolver import AsyncResolver
        bindings = {**IMPLICIT_BINDINGS, **self.bindings}
        return AsyncResolver(Design(bindings=bindings, modules=self.modules))

    def to_graph(self):
        return self.to_resolver().to_blocking()

    def run(self, f, modules=None):
        return self.to_graph(modules).run(f)

    def provide(self, target: Union[str, Type[T]]) -> T:
        """
        :param target: provided name
        :param modules: modules to use for graph construction
        :return:
        """
        return self.to_resolver().to_blocking().provide(target)

    def copy(self):
        return self.__class__(
            bindings=self.bindings.copy(),
            modules=copy(self.modules),
        )

    def map_value(self, src_key, f):
        """
        :param src_key:
        :param f:
        :return: Design
        """
        mapped_binding = self.bindings[src_key].map(f)
        return self + Design({src_key: mapped_binding})

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

    def __contains__(self, item: IBindKey):
        return item in self.bindings

    def __getitem__(self, item: IBindKey | str):
        if isinstance(item, str):
            item = StrBindKey(item)
        assert isinstance(item, IBindKey), f"item must be IBindKey or a str, but got {type(item)}"
        return self.bindings[item]

    def __str__(self):
        return f"Design(len={len(self.bindings)})"

    def __repr__(self):
        return str(self)

    def table_str(self):
        import tabulate
        binds = tabulate.tabulate(sorted(list(self.bindings.items())))
        return binds

    def to_str_dict(self):
        res = dict()
        for k, v in self.bindings.items():
            match v:
                case BindInjected(InjectedFunction(f, args)):
                    res[k] = f.__name__
                case BindInjected(InjectedPure(value)):
                    res[k] = str(value)
                case any:
                    res[k] = str(any)
        return res

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

    def diff(self, other):
        from pinjected.di.util import get_dict_diff
        d = get_dict_diff(self.bindings, other.bindings)
        return d

    def inspect_picklability(self):
        from pinjected.di.util import check_picklable
        from loguru import logger
        logger.info(f"checking picklability of bindings")
        check_picklable(self.bindings)
        logger.info(f"checking picklability of modules")
        check_picklable(self.modules)

    def add_modules(self, *modules):
        return self + Design(modules=list(modules))

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
        resolver = DependencyResolver(self)
        return resolver.purified_design(target).unbind('__resolver__').unbind('session').unbind('__design__')


@dataclass
class DesignOverrideContext:
    src: Design
    callback: Callable[[Self], None]
    depth: int
    target_vars: dict = field(default_factory=dict)

    def __enter__(self):
        frame = inspect.currentframe()
        parent = frame.f_back
        # get parent global variables
        parent_globals = parent.f_globals
        global_ids = {k: id(v) for k, v in parent_globals.items()}
        from loguru import logger
        logger.debug(global_ids)
        self.last_global_ids = global_ids

    def __exit__(self, exc_type, exc_val, exc_tb):
        from loguru import logger
        frame = inspect.currentframe()
        parent = frame.f_back
        # get parent global variables
        parent_globals = parent.f_globals
        global_ids = {k: id(v) for k, v in parent_globals.items()}
        changed_keys = []
        for k in global_ids:
            if k in self.last_global_ids:
                if global_ids[k] != self.last_global_ids[k]:
                    changed_keys.append(k)
            else:
                changed_keys.append(k)
        logger.debug(f"global_ids:{global_ids}")
        # find instance of DelegatedVar and Injected in the changed globals
        target_vars = dict()
        for k in changed_keys:
            v = parent_globals[k]
            if isinstance(v, DelegatedVar):
                target_vars[k] = v
            if isinstance(v, Injected):
                target_vars[k] = v
        self.target_vars = target_vars
        self.callback(self)
