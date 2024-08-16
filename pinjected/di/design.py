import inspect
from dataclasses import dataclass, field, replace
from functools import wraps
from typing import TypeVar, List, Dict, Union, Callable, Type, Optional

from cytoolz import merge
from makefun import create_function

from pinjected.di.design_interface import ProvisionValidator, Design
from pinjected.v2.callback import IResolverCallback
from pinjected.di.app_injected import EvaledInjected
from pinjected.di.implicit_globals import IMPLICIT_BINDINGS
from pinjected.di.injected import Injected
from pinjected.di.injected import extract_dependency_including_self, InjectedPure, InjectedFunction
# from pinjected.di.util import get_class_aware_args, get_dict_diff, check_picklable
from pinjected.di.proxiable import DelegatedVar
from pinjected.v2.binds import IBind, BindInjected, ExprBind
from pinjected.v2.keys import IBindKey, StrBindKey

T = TypeVar("T")
U = TypeVar("U")


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
class MergedDesign(Design):
    srcs: List[Design]

    @property
    def children(self):
        return self.srcs

    def __contains__(self, item: IBindKey):
        return any(item in src for src in self.srcs)

    def __getitem__(self, item: IBindKey | str):
        for src in reversed(self.srcs):  # the last one takes precedence
            if item in src:
                res = src[item]
                assert isinstance(res, IBind), f"item must be IBind, but got {type(res)}=={res}"
                return res
        raise KeyError(f"{item} not found in any of the sources")

    @property
    def bindings(self) -> Dict[IBindKey, IBind]:
        return merge(*[src.bindings for src in self.srcs])

    @property
    def validations(self) -> Dict[IBindKey, ProvisionValidator]:
        return merge(*[src.validations for src in self.srcs])

    def __repr__(self):
        return f"MergedDesign(srcs={len(self.srcs)})"

    def __add__(self, other):
        return MergedDesign(self.srcs + [other])


@dataclass
class AddValidation(Design):
    src: Design
    _validations: Dict[IBindKey, ProvisionValidator]

    def __contains__(self, item: IBindKey):
        return item in self.src

    def __getitem__(self, item: IBindKey | str):
        return self.src[item]

    @property
    def bindings(self) -> Dict[IBindKey, IBind]:
        return self.src.bindings

    @property
    def validations(self) -> Dict[IBindKey, ProvisionValidator]:
        return self._validations | self.src.validations

    @property
    def children(self):
        return [self.src]


"""
All designs are merged with '+'. 
so, those things added doesnt require any design information...
So basically the design tree becomes a tree from MergedDesign,
where the leaves are the actual designs.
wait, in that case, for the priorities to work, the merged design needs to be fixed.

"""


@dataclass
class MetaDataDesign(Design):
    def __contains__(self, item: IBindKey):
        return False

    def __getitem__(self, item: IBindKey | str) -> IBind:
        raise KeyError(f"no such key {item}")

    @property
    def bindings(self) -> Dict[IBindKey, IBind]:
        return dict()

    @property
    def validations(self) -> Dict[IBindKey, ProvisionValidator]:
        return dict()

    @property
    def children(self):
        return []


@dataclass
class AddSummary(MetaDataDesign):
    summary: str


@dataclass
class AddTags(MetaDataDesign):
    tags: List[str]


@dataclass
class DesignImpl(Design):
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

        d = EmptyDesign.bind_instance(
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

        d1 = EmptyDesign.bind_instance(
            a=0
        )
        d2 = EmptyDesign.bind_instance(
            b=1
        )
        d3 = EmptyDesign.bind_instance(
            b=0
        )

        # The `+` operator combines designs. If the same binding exists in both designs,
        # the one from the rightmost design (latest) will take precedence.
        assert (d1 + d2).provide("b") == 1  # 'b' from d2 takes precedence
        assert (d1 + d2 + d3).provide("b") == 0  # 'b' from d3 overrides the others

    This feature ensures that ``Design`` instances are composable and adaptable, providing
    a robust foundation for building complex, modular applications with dependency injection.
    """

    _bindings: Dict[IBindKey, IBind] = field(default_factory=dict)

    @property
    def children(self):
        return []

    @property
    def validations(self) -> Dict[IBindKey, ProvisionValidator]:
        return dict()

    @property
    def bindings(self):
        return self._bindings

    def __getstate__(self):
        res = dict(
            _bindings=self._bindings,
        )
        return res

    def __setstate__(self, state):
        for k, v in state.items():
            setattr(self, k, v)

    def bind_instance(self, **kwargs, ):
        """
        Here, I need to find the CodeLocation for each binding.
        :param kwargs:
        :param __binding_metadata__: a dict of [str,BindMetadata]
        :return:
        """
        bindings = self._bindings.copy()
        for k, v in kwargs.items():
            if isinstance(v, type):
                from loguru import logger
                logger.warning(f"{k} is bound to class {v} with 'bind_instance' do you mean 'bind_class'?")
            bindings[StrBindKey(k)] = BindInjected(Injected.pure(v))
        return DesignImpl(_bindings=bindings)

    @staticmethod
    def to_bind(tgt) -> IBind:
        from loguru import logger
        match tgt:
            case IBind():
                return tgt
            case type():
                return BindInjected(Injected.bind(tgt))
            case EvaledInjected():
                return ExprBind(tgt)
            case DelegatedVar():
                return ExprBind(tgt.eval())
            case Injected():
                return BindInjected(tgt)
            case non_func if not callable(non_func):
                logger.warning(f"{tgt}: non-callable or non-injected is passed to bind_provider. fixing automatically.")
                return BindInjected(Injected.pure(non_func))
            case func if callable(func):
                return BindInjected(Injected.bind(func))
            case _:
                raise ValueError(f"cannot bind {tgt}")

    def bind_provider(self, **kwargs: Union[Callable, Injected]):
        bindings = self.bindings.copy()
        for k, v in kwargs.items():
            bindings[StrBindKey(k)] = self.to_bind(v)
        return DesignImpl(_bindings=bindings)

    def add_metadata(self, **kwargs: "BindMetadata") -> "Design":
        res = self
        for k, meta in kwargs.items():
            key = StrBindKey(k)
            bind: IBind = self.bindings[key]
            res += DesignImpl(
                _bindings={key: bind.update_metadata(meta)}
            )
        return res

    def to_resolver(self, callback: Optional[IResolverCallback] = None):
        from pinjected.v2.resolver import AsyncResolver, BaseResolverCallback
        bindings = {**IMPLICIT_BINDINGS, **self.bindings}
        if callback is None:
            #callback = BaseResolverCallback()
            callbacks = []
        else:
            assert isinstance(callback, IResolverCallback)
            callbacks=[callback]
        return AsyncResolver(
            DesignImpl(_bindings=bindings),
            callbacks=callbacks
        )

    def to_graph(self):
        return self.to_resolver().to_blocking()

    def run(self, f):
        return self.to_graph().run(f)

    def provide(self, target: Union[str, Type[T]]) -> T:
        """
        :param target: provided name
        :param modules: modules to use for graph construction
        :return:
        """
        return self.to_resolver().to_blocking().provide(target)

    def copy(self):
        return DesignImpl(
            _bindings=self.bindings.copy(),
        )

    def map_value(self, src_key, f):
        """
        :param src_key:
        :param f:
        :return: Design
        """
        mapped_binding = self.bindings[src_key].map(f)
        return self + DesignImpl({src_key: mapped_binding})

    def keys(self):
        return self.bindings.keys()

    def unbind(self, key) -> "Design":
        if key in self.bindings:
            copied = self.bindings.copy()
            del copied[key]
            return replace(self,
                           _bindings=copied
                           )
        return self

    def __contains__(self, item: IBindKey):
        return item in self.bindings

    def __getitem__(self, item: IBindKey | str):
        if isinstance(item, str):
            item = StrBindKey(item)
        assert isinstance(item, IBindKey), f"item must be IBindKey, but got {type(item)}=={item}"
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

