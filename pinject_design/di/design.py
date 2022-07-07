import abc
import inspect
from dataclasses import dataclass
from functools import wraps
from typing import TypeVar, Generic, Callable, Union, Dict, List

from frozendict import frozendict
from loguru import logger
from makefun import create_function

from pinject_design.di.injected import Injected, extract_dependency_including_self, extract_dependency

T = TypeVar("T")
U = TypeVar("U")


@dataclass
class PinjectConfigure:
    kwargs: Dict  # a dict like:{to_class=A} / {to_instance=0}

    def __hash__(self):
        return hash(frozendict(**self.kwargs))


@dataclass
class PinjectProvider:
    method: Callable  # a callable with (self,dep1,dep2) signatures...

    # might be annotated with pinject's annotations..
    # pinject ads an attribute to an annotated function for marking..
    # which is not something I prefer though...
    # ok I should stop using pinject's features

    def __post_init__(self):
        # if self is not in method signature, this will add it.
        assert self.method is not None, "PinjectProvider created with method==None!"
        if callable(self.method):
            self.method = ensure_self_arg(self.method)
            # we need to make sure the function's name starts with provide_
        else:
            # may this class is used for pampy pattern matching..
            pass

    def __hash__(self):
        return hash(self.method)


class Bind(Generic[T], metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def to_pinject_binding(self) -> Union[PinjectConfigure, PinjectProvider]:
        pass

    def map(self, f: Callable[[T], U]) -> "Bind[U]":
        return MappedBind(self, f)

    @staticmethod
    def provider(f: Callable):
        return FunctionProvider(f)

    @staticmethod
    def injected(injected: Injected):
        return InjectedProvider(injected)

    @staticmethod
    def instance(instance: object):
        return PinjectBind(kwargs=dict(to_instance=instance))

    @staticmethod
    def clazz(cls: type):
        return PinjectBind(kwargs=dict(to_class=cls))

    def to_injected(self) -> Injected:
        return bind_to_injected(self)


def map_wrap(src, f):
    @wraps(src)
    def wrapper(*args, **kwargs):
        return f(src(*args, **kwargs))

    wrapper.__signature__ = inspect.signature(src)
    return wrapper


def pinject_to_provider(binding: Union[PinjectConfigure, PinjectProvider]):
    from pampy import match, _
    new_provider = match(binding,
                         PinjectConfigure({"to_class": _}), lambda cls: cls,  # create a function provider
                         PinjectConfigure({"to_instance": _}), lambda item: lambda: item,
                         PinjectProvider(_), lambda f: f
                         )
    return new_provider


@dataclass
class MappedBind(Bind[U]):
    src: Bind[T]
    f: Callable[[T], U]

    def to_pinject_binding(self) -> Union["PinjectConfigure", "PinjectProvider"]:
        binding = self.src.to_pinject_binding()
        new_provider = pinject_to_provider(binding)
        mapped = map_wrap(new_provider, self.f)
        return PinjectProvider(mapped)


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


def bind_to_injected(bind: Bind):
    if isinstance(bind, PinjectBind) and "to_class" in bind.kwargs:
        cls = bind.kwargs["to_class"]
        return Injected.bind(cls)
    elif isinstance(bind, InjectedProvider):
        return bind.src
    pb = bind.to_pinject_binding()
    provider = pinject_to_provider(pb)
    provider = remove_kwargs_from_func(provider, ["self"])
    return Injected.bind(provider)


# jetbrains://idea/navigate/reference?project=archpainter&path=notes/organized/mac/check_fid_and_generated.ipynb

# A contract of Bind is that it is possible to return
# Configure/Provider to be assigned to BindingSpec given a key name.


# in order to make this class picklable, we need to postpone the wrapping process until to_binding_spec() call.
class ProviderTrait(Bind[T]):
    @property
    @abc.abstractmethod
    def provider(self):
        pass

    def to_pinject_binding(self) -> Union["PinjectConfigure", "PinjectProvider"]:
        provider = self.provider
        assert provider is not None, "provider is None for some reason!"
        return PinjectProvider(provider)


@dataclass
class InjectedProvider(ProviderTrait[T]):
    src: Injected[T]

    @property
    def provider(self):
        return self.src.get_provider()


@dataclass
class FunctionProvider(ProviderTrait[T]):
    f: Callable

    def __post_init__(self):
        assert self.f is not None, "FunctioProvider created with None!"
        self._dependencies = extract_dependency(self.f)

    @property
    def provider(self):
        return self.f


# and anything that converts to provider


def ensure_provider_name(f):
    if not f.__name__.startswith("provide_"):
        f.__name__ = "provide_" + f.__name__
    return f


def ensure_self_arg(func, fname: str = None):
    """
    adds a self arg in to func signature if not present
    :param func:
    :return:
    """
    assert func is not None
    argspec = inspect.getfullargspec(func)
    if argspec.args and argspec.args[0] == "self":
        return func
    assert "self" not in argspec.args, f"{argspec.args}"
    # source = inspect.getsource(func)
    module = inspect.getmodule(func)
    # module can be None if func is from the pickled.
    if fname is None:
        try:
            lines, ln = inspect.getsourcelines(func)
            fn = func.__name__.replace("<", "").replace(">", "")
            fname = f"""{module.__name__.replace(".", "_")}_ln_{ln}_{fn}"""
        except OSError as ose:
            fn = func.__name__.replace("<", "").replace(">", "")
            fname = f"""{module.__name__.replace(".", "_")}_{fn}"""
        except AttributeError as ae:
            logger.warning(f"could not set reasonable func name. better provide fname as argument!")
            fname = f"""unknwon_module_function"""

    assert not isinstance(argspec.args, str)
    signature = f"""{fname}({" ,".join(["self"] + (argspec.args or []))})"""

    # logger.error(source)

    def impl(self, *args, **kwargs):
        return func(*args, **kwargs)  # gets multiple values for self

    assert len(argspec.kwonlyargs) == 0, "providing method cannot have any kwonly args"
    return create_function(signature, impl)


@dataclass
class PinjectBind(Bind):
    kwargs: Dict

    def __hash__(self):
        return hash(frozendict(**self.kwargs))

    def to_pinject_binding(self) -> Union[PinjectConfigure, PinjectProvider]:
        return PinjectConfigure(self.kwargs)

@dataclass
class MetaBind(Bind):
    src:Bind
    metadata:dict
    def to_pinject_binding(self) -> Union[PinjectConfigure, PinjectProvider]:
        return self.src.to_pinject_binding()
