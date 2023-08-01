import inspect
from copy import copy
from dataclasses import dataclass, field, replace
from itertools import chain
from pprint import pformat
from typing import Union, Type, TypeVar, Callable, Dict, Any

import cloudpickle
from cytoolz import merge
from makefun import create_function
from returns.result import safe, Failure, Success

from pinjected.di.bindings import InjectedBind, Bind
from pinjected.di.graph import MyObjectGraph, IObjectGraph
from pinjected.di.injected import Injected, InjectedPure, InjectedFunction
from pinjected.di.proxiable import DelegatedVar

# is it possible to create a binding class which also has an ability to dynamically add..?
# yes. actually.
T = TypeVar("T")


def rec_valmap(f, tgt: dict):
    res = dict()
    for k, v in tgt.items():
        if isinstance(v, dict):
            res[k] = rec_valmap(f, v)
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


class ErrorWithTrace(BaseException):
    def __init__(self, src: BaseException, trace: str):
        super().__init__()
        self.src = src
        self.trace = trace

    def __reduce__(self):
        return (ErrorWithTrace, (self.src, self.trace))

    def __str__(self):
        return f"{self.src}\n {self.trace}"


def my_safe(f):
    def impl(*args, **kwargs):
        try:
            return Success(f(*args, **kwargs))
        except Exception as e:
            import traceback
            trace = "\n".join(traceback.format_exception(e))

            return Failure(ErrorWithTrace(
                e,
                trace
            ))

    return impl


def check_picklable(tgt: dict):
    cloud_dumps_try = my_safe(cloudpickle.dumps)
    cloud_loads_try = my_safe(cloudpickle.loads)
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
        raise RuntimeError("this object is not picklable. check the error messages above.") from res.failure()
    # logger.info(res)





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

    def to_class(self, cls: type):
        assert isinstance(cls, type), f"binding must be a class! got:{cls} for key:{self.src}"
        return self.src + Design({self.key:InjectedBind(Injected.bind(cls))})

    def to_instance(self, instance):
        return self.src + Design({self.key:InjectedBind(Injected.pure(instance))})

    def to_provider(self,provider):
        return self.src + Design({self.key:InjectedBind(Injected.bind(provider))})


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
    match o:
        case InjectedBind(InjectedFunction(func, _)):
            return func.__name__
        case InjectedBind(InjectedPure(value)):
            return value
        case any:
            return any


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
        match (ak,bk):
            case (Subject(),Subject()):
                flag = True
            case (a,b):
                flag = a != b
            case _:
                raise RuntimeError("this should not happen")
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

    def __add__(self, other: Union["Design", Dict[str, Bind]]):
        other = self._ensure_dbc(other)
        return self.merged(other)

    def bind(self, key: str) -> DesignBindContext:
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

    def bind_instance(self, **kwargs):
        x = self
        for k, v in kwargs.items():
            if isinstance(v, type):
                from loguru import logger
                logger.warning(f"{k} is bound to class {v} with 'bind_instance' do you mean 'bind_class'?")
            x += Design({k: InjectedBind(InjectedPure(v))})
        return x

    def bind_provider(self, **kwargs: Union[Callable, Injected]):
        from loguru import logger
        x = self
        for k, v in kwargs.items():
            # logger.info(f"binding provider:{k}=>{v}")
            def parse(item):
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

    def to_graph(self, modules=None, classes=None) -> IObjectGraph:
        # So MyObjectGraph's session is still corrupt?
        design = self + Design(
            modules=modules or [],
            classes=classes or []
        )
        return MyObjectGraph.root(design)

    def run(self, f, modules=None, classes=None):
        return self.to_graph(modules, classes).run(f)

    def provide(self, target: Union[str, Type[T]], modules=None, classes=None) -> T:
        """
        :param target: provided name
        :param modules: modules to use for graph construction
        :return:
        """
        return self.to_graph(modules=modules, classes=classes).provide(target, level=4)

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

    def to_vis_graph(self):
        from pinjected.visualize_di import DIGraph
        return DIGraph(self)


EmptyDesign = Design()


# mapping is another layer of complication.
# good way is to create a MappedDesign class which is not a subclass of a Design
# only MappedDesign or Design can be __add__ ed to this class
# calling to_design converts all lazy mapping into providers
# so if anything is missing then fails.

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


def instances(**kwargs):
    for k, v in kwargs.items():
        assert not isinstance(v,
                              DelegatedVar), f"passing delegated var with Injected context is forbidden, to prevent human error."
        assert not isinstance(v,
                              Injected), f"passing Injected to 'instances' is forbidden, to prevent human error. use bind_instance instead."
    return Design().bind_instance(**kwargs)


def providers(**kwargs):
    return Design().bind_provider(**kwargs)


def classes(**kwargs):
    return Design().bind_class(**kwargs)


def injecteds(**kwargs):
    return Design().bind_provider(**kwargs)
