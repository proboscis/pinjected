import abc
import inspect
from copy import copy
from dataclasses import dataclass, field, replace
from functools import wraps
from itertools import chain
from pprint import pformat
from typing import Union, Type, TypeVar, Callable, Dict, Any

import cloudpickle
import pinject
from cytoolz import merge, valmap, itemmap
from makefun import create_function, wraps
from pampy import match
from pinject import BindingSpec
from pinject.scoping import SingletonScope, BindableScopes, SINGLETON
from pinject_design.di.design import Bind, FunctionProvider, ProviderTrait, InjectedProvider, PinjectConfigure, \
    PinjectProvider, ensure_self_arg, PinjectBind
from pinject_design.di.graph import ExtendedObjectGraph
from pinject_design.di.injected import Injected
from returns.result import safe, Failure
from tabulate import tabulate

from pinject_design.di.session import SessionScope

prototype = pinject.provides(in_scope=pinject.PROTOTYPE)
# is it possible to create a binding class which also has an ability to dynamically add..?
# yes. actually.
T = TypeVar("T")


def rec_valmap(f, tgt: dict):
    res = dict()
    for k, v in tgt.items():
        if isinstance(v, dict):
            res[k] = rec_valmap(tgt[k], v)
        else:
            res[k] = f(v)
    return res


def rec_val_filter(f, tgt: dict):
    res = dict()
    for k, v in tgt.items():
        if isinstance(v, dict):
            res[k] = rec_val_filter(f, v)
        elif f(v):
            res[k] = v
    return res


def check_picklable(tgt: dict):
    cloud_dumps_try = safe(cloudpickle.dumps)
    cloud_loads_try = safe(cloudpickle.loads)
    res = cloud_dumps_try(tgt).bind(cloud_loads_try)

    if isinstance(res, Failure):
        # target_check = valmap(cloud_dumps_try, tgt)
        rec_check = rec_valmap(lambda v: (cloud_dumps_try(v), v), tgt)
        failures = rec_val_filter(lambda v: isinstance(v[0], Failure), rec_check)
        # failures = [(k, v, tgt[k]) for k, v in target_check.items() if isinstance(v, Failure)]

        from loguru import logger
        logger.error(f"Failed to pickle target: {pformat(failures)}")
        logger.error(f"if the error message contains EncodedFile pickling error, "
                     f"check whether the logging module is included in the target object or not.")
        raise RuntimeError("this object is not picklable. check the error messages above.")
    # logger.info(res)


def inject_proto(all_except=None, arg_names=None):
    """injects provider with prototype context"""

    def _inner(f):
        return pinject.inject(all_except=all_except, arg_names=arg_names)(prototype(f))

    return _inner


def method_to_function(method):
    """
    converts a class method to a function
    """
    argspec = inspect.getfullargspec(method)
    assert not isinstance(argspec.args, str)
    # assert not isinstance(argspec.varargs,str)
    signature = f"""f_of_{method.__name__}({" ,".join((argspec.args or []))})"""

    def impl(self, *args, **kwargs):
        return method(*args, **kwargs)  # gets multiple values for self

    assert len(argspec.kwonlyargs) == 0, "providing method cannot have any kwonly args"
    return create_function(signature, impl)


def none_provider(func):
    argspec = inspect.getfullargspec(func)
    signature = f"""none_provider({" ,".join((argspec.args or []) + (argspec.varargs or []))})"""

    def impl(*args, **kwargs):
        func(*args, **kwargs)  # gets multiple values for self
        return "success of none_provider"

    assert len(argspec.kwonlyargs) == 0, "providing method cannot have any kwonly args"
    return create_function(signature, impl)


class DesignBindContext:
    def __init__(self, src: "Design", key: str):
        self.src = src
        self.key = key

    def to_class(self, cls: type, **kwargs):
        assert isinstance(cls, type), f"binding must be a class! got:{cls} for key:{self.src}"
        return self.src.bind_imm(self.key, to_class=cls, **kwargs)

    def to_instance(self, instance, **kwargs):
        return self.src.bind_imm(self.key, to_instance=instance, **kwargs)

    def to_provider(self, provider, all_except=None, arg_names=None, in_scope=None):
        return self.src.bind_provider_imm(self.key, provider, all_except=all_except, arg_names=arg_names,
                                          in_scope=in_scope)


def extract_argnames(func):
    spec = inspect.getfullargspec(func)
    return spec.args


def get_class_aware_args(f):
    args = inspect.getfullargspec(f).args
    if isinstance(f, type) and "self" in args:
        args.remove("self")
    return args


def getitem_opt(o, k):
    return safe(o.__getitem__)(k)


def to_readable_name(o):
    from pampy import match, _
    return match(o,
                 DirectPinjectProvider(_), lambda method: method.__name__,
                 PinjectProviderBind, lambda ppb: (ppb.f.__name__),
                 PinjectBind({"to_instance": _}), lambda i: i,
                 PinjectBind({"to_class": _}), lambda c: c.__name__,
                 Any, lambda x: x
                 )


def try_import_subject():
    try:
        from rx.subject import Subject
        return Subject
    except Exception as e:
        from rx.subjects import Subject
        return Subject


def get_dict_diff(a: dict, b: dict):
    all_keys = list(sorted(set(a.keys()) | set(b.keys())))
    all_keys.remove("opt")
    # TODO check both contains transform design
    # all_keys.remove("base_train_transform_design")
    # all_keys.remove("base_test_transform_design")
    all_keys.remove("design")
    data = []
    Subject = try_import_subject()
    for k in all_keys:

        ak = getitem_opt(a, k).map(to_readable_name).value_or(None)
        bk = getitem_opt(b, k).map(to_readable_name).value_or(None)
        flag = match((ak, bk),
                     (Subject, Subject), lambda a, b: True,
                     # (np.ndarray, np.ndarray), lambda a, b: (a != b).any(),
                     # (np.ndarray, Any),lambda a,b:False,
                     # (Any,np.ndarray),lambda a,b:False,
                     (Any, Any), lambda a, b: a != b
                     )
        if flag:
            data.append((k, ak, bk))

    return data


T = TypeVar("T")


@dataclass
class Design:
    # TODO implement __getstate__ and __setstate__ with dill! so that this can be pickled.
    # basically a State/Free Monad on Pinject's BindingSpec
    """
    This is an injection binding class which can be used to compose configures and providers.
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
        # ah, so this pickling checker is a bit of a problem
        # check_picklable(self.bindings)
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

    def __add__(self, other: Union["Design", BindingSpec, Dict[str, Bind]]):
        other = self._ensure_dbc(other)
        return self.merged(other)

    def bind(self, key: str) -> DesignBindContext:
        return DesignBindContext(self, key)

    def _ensure_dbc(self, other: Union["Design", BindingSpec, Dict[str, Bind]]):
        return match(other,
                     BindingSpec, lambda o: Design.gather_spec(o),
                     Design, lambda d: d,
                     Dict[str, Bind], lambda d: Design(d)
                     )

    def _merge_multi_binds(self, src, dst):
        # src = Map.of(**src)
        # dst = Map.of(**dst)
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

    def bind_provider_imm(self, key, f, all_except=None, arg_names=None, in_scope=None):
        def raise_unhandled(any):
            raise RuntimeError(f"unknown input type for bind_provider_imm! key:{key}, provider:{f}")

        bind = match(f,
                     Injected, lambda i: Design({key: InjectedProvider(i)}),
                     ProviderTrait, lambda pt: Design({key: pt}),
                     callable, lambda c: Design(
                {key: PinjectProviderBind(f, all_except=all_except, arg_names=arg_names, in_scope=in_scope)}),
                     Any, raise_unhandled
                     )
        res = self + bind
        return res

    def bind_imm(self, key, **kwargs):
        from pampy import _
        return self + match(kwargs,
                            {"to_class": Injected}, lambda injected: Design(bindings={key: InjectedProvider(injected)}),
                            _, Design(bindings={key: PinjectBind(kwargs)})
                            )

    def bind_instance(self, **kwargs):
        x = self
        for k, v in kwargs.items():
            if isinstance(v, type):
                from loguru import logger
                logger.warning(f"{k} is bound to class {v} with 'bind_instance' do you mean 'bind_class'?")
            x = x.bind(k).to_instance(v)
        return x

    def bind_provider(self, **kwargs: Union[Callable, Injected]):
        from loguru import logger
        x = self
        for k, v in kwargs.items():
            # logger.info(f"binding provider:{k}=>{v}")
            if isinstance(v, type):
                logger.warning(f"{k}->{v}: class is used for bind_provider. fixing automatically.")
                x = x.bind(k).to_class(v)
            if isinstance(v, Injected):
                x = x.bind(k).to_provider(v)
            elif not callable(v):
                logger.warning(
                    f"{k}->{v}: non-callable or non-injected is passed to bind_provider. fixing automatically.")
                x = x.bind(k).to_instance(v)
            else:
                x = x.bind(k).to_provider(v)
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

    def to_graph(self, modules=None, classes=None) -> ExtendedObjectGraph:
        modules = self.modules + (modules or [])
        classes = self.classes + (classes or [])
        # logger.info(f"to_graph:\n\t{pformat(modules)}\n\t{pformat(classes)}")
        g = pinject.new_object_graph(
            modules=modules,
            binding_specs=[self.to_binding_spec()],
            classes=classes
        )
        g._obj_provider._bindable_scopes = BindableScopes(
            id_to_scope={SINGLETON: SessionScope()}
        )
        return ExtendedObjectGraph(self, g)

    def run(self, f, modules=None, classes=None):
        return self.to_graph(modules, classes).run(f)

    def provide(self, target: Union[str, Type[T]], modules=None, classes=None) -> T:
        """
        :param target: provided name
        :param modules: modules to use for graph construction
        :return:
        """
        return self.to_graph(modules=modules, classes=classes).provide(target)

    @staticmethod
    def gather_spec(b: BindingSpec) -> "Design":
        assert isinstance(b, BindingSpec)
        dep_spec = Design()
        for dep in b.dependencies() or []:
            spec = Design.gather_spec(dep)
            # logger.debug(f"dependency:{spec}")
            dep_spec += spec
        spec = Design()

        if hasattr(b, "configure"):
            @safe
            def accumulate():
                def binder(key, **kwargs):
                    nonlocal spec
                    spec = spec.bind_imm(key, **kwargs)

                # logger.debug(f"configuring binder:{b}")
                b.configure(binder)

            accumulate()
        for item in dir(b):
            if item.startswith("provide"):
                method = getattr(b, item)
                if callable(method):
                    # logger.debug(f"binding from spec:{item}")
                    k = item.replace("provide_", "", 1)
                    spec = spec + Design({k: DirectPinjectProvider(getattr(b, item))})
                    assert k in spec
        res = dep_spec + spec
        debug = res.to_binding_spec()
        for item in dir(b):
            if item.startswith("provide"):  # and callable(getattr(b,item)):
                k = item.replace("provide_", "", 1)
                # how the hell a function is not callable
                # ok the item is PinjectProvider, not function.
                # how can BindingSpec have an attribute as PinjectProvider?
                assert k in res, f"{k} not in res. key in spec?={k in spec},obj:{getattr(b, item)},callable:{callable(getattr(b, item))}"
                assert item in dir(debug)
        return res

    @staticmethod
    def traverse_specs(*bindings: BindingSpec):
        spec = Design()
        for b in bindings:
            spec = spec + b
        # logger.debug(f"traversed binding:\n\t{spec}")
        return spec

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
        applied_bind = Bind.injected(bind.to_injected().apply_injected_function(injected_func))
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
        from pampy import _
        for k, v in self.bindings.items():
            res[k] = match(v,
                           FunctionProvider, lambda fp: fp.f.__name__,
                           InjectedProvider, lambda i: str(i),
                           PinjectBind({'to_class': _}), lambda cls: str(cls),
                           PinjectBind({'to_instance': _}), lambda ins: str(ins),
                           _, lambda any: str(any)
                           )
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

    def to_binding_spec(self):
        """Generate a BindingSpec class for pinject and returns its instance."""

        design = self.build()
        bindings = {k: v.to_pinject_binding() for k, v in design.bindings.items()}
        configures = {k: v for k, v in bindings.items() if isinstance(v, PinjectConfigure)}
        # configures = bindings.filter(lambda k, v: isinstance(v, PinjectConfigure))
        providers = {k: v for k, v in bindings.items() if isinstance(v, PinjectProvider)}
        providers = {k: self._ensure_provider_name(k, v.method) for k, v in providers.items()}

        # providers = itemmap(lambda t: self._ensure_provider_name(t[0], t[1].method), providers)

        # providers = bindings.filter(lambda k, v: isinstance(v, PinjectProvider)).map(
        #     lambda k, v: self._ensure_provider_name(k, v.method)
        # )

        def configure(self, bind):
            for c, v in dict(configures).items():
                # logger.info(f"bind :{v.kwargs}")
                bind(c, **v.kwargs)

        DynamicBinding = type("DynamicBinding", (BindingSpec,),
                              {
                                  "configure": configure,
                                  **{f"provide_{k}": v for k, v in providers.items()},
                              })

        return DynamicBinding()

    def _ensure_provider_name(self, k, method):
        """set appropriate name for provider function to be recognized by pinject"""
        from loguru import logger
        name = f"provide_{k}"
        if not method.__name__ == name:
            # there are cases where you cannot directly set __name__ attribute.
            # and sometimes pinject.inject decorator is already applied so wrapping that again is not appropriate
            # so, the solution is to first try setting __name__ and then try wrapping if failed.
            try:
                method.__name__ = name
                return method
            except AttributeError as ae:
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
        d = get_dict_diff(self.bindings, other.bindings)
        return d

    def inspect_picklability(self):
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


EmptyDesign = Design()


@dataclass
class DirectPinjectProvider(Bind):
    method: Callable

    def to_pinject_binding(self) -> Union[PinjectConfigure, PinjectProvider]:
        return PinjectProvider(self.method)

    def __hash__(self):
        return hash(self.method)


# mapping is another layer of complication.
# good way is to create a MappedDesign class which is not a subclass of a Design
# only MappedDesign or Design can be __add__ ed to this class
# calling to_design converts all lazy mapping into providers
# so if anything is missing then fails.

class DynamicSpec(BindingSpec, metaclass=abc.ABCMeta):
    def __init__(self):
        container = Design()
        container = self.dynamic_configure(container)
        self._dependencies = [container.to_binding_spec()]

    @abc.abstractmethod
    def dynamic_configure(self, binder: Design) -> Design:
        pass

    def configure(self, bind):
        pass

    def dependencies(self):
        return self._dependencies


def _patched_provide(self, binding_key, default_provider_fn):
    with self._rlock:
        d: dict = self._binding_key_to_instance
        if binding_key not in d:
            val = default_provider_fn()
            d[binding_key] = val
        return d[binding_key]


def patch_pinject_singleton_scope():
    from loguru import logger
    logger.warning(f"patching pinject's SingletonScope to produce better exception")
    SingletonScope.provide = _patched_provide
    logger.warning(f"patching done")


patch_pinject_singleton_scope()


def _get_external_type_name(thing):
    """patch pinject's _get_external_type_name to accept pickled function"""
    qualifier = thing.__qualname__
    name = qualifier.rsplit('.', 1)[0]
    if hasattr(inspect.getmodule(thing), name):
        cls = getattr(inspect.getmodule(thing), name)
        if isinstance(cls, type):
            return cls.__name__

    res = inspect.getmodule(thing)  # .__name__
    if res is None:
        return "unknown_module"
    return res.__name__


def patch_pinject_get_external_type_name():
    import pinject.locations
    from loguru import logger
    logger.warning(f"patching pinject's _get_external_type_name to accept pickled function")
    pinject.locations._get_external_type_name = _get_external_type_name


patch_pinject_get_external_type_name()


# patch_pinject_singleton_scope()
@dataclass
class PinjectProviderBind(Bind):
    """use this to keep things picklable"""
    f: Callable
    all_except: Any
    arg_names: Any
    in_scope: Any

    def __post_init__(self):
        assert self.f is not None, "PinjectProviderBind cannot have None as f."
        if self.f.__name__ == "<lambda>":
            self.f.__name__ = "_lambda_"
        self._fname = self.f.__name__
        assert self._fname is not None, f"provided function has no name.:{self.f}"
        self._signature = inspect.signature(self.f)

    def provider_for_binding_spec(self):
        # so first you need to convert a method in to function
        assert self.f is not None
        f = self.f
        if "__name__" not in dir(f):
            f = method_to_function(f)
        # now ensure the function has self arg
        f = ensure_self_arg(f, fname=self._fname)

        @wraps(f)  # called 78 times
        def wrapper(*args, **kwargs):
            return f(*args, **kwargs)

        wrapper.__name__ = f.__name__
        all_except = self.all_except
        arg_names = self.arg_names
        in_scope = self.in_scope
        if all_except is not None or arg_names is not None:
            wrapper = inject_proto(all_except=all_except, arg_names=arg_names)(wrapper)
        if in_scope is not None:
            wrapper = pinject.provides(in_scope=in_scope)(wrapper)
        return wrapper

    def to_pinject_binding(self) -> Union[PinjectConfigure, PinjectProvider]:
        return PinjectProvider(self.provider_for_binding_spec())

    def __getstate__(self):
        return dict(
            f=self.f,
            all_except=self.all_except,
            arg_names=self.arg_names,
            in_scope=self.in_scope,
            _fname=self._fname,
            _signature=self._signature
        )

    def __setstate__(self, state):
        for k, v in state.items():
            setattr(self, k, v)
        assert self.f is not None
