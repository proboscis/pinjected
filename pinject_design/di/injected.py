import abc
import functools
import inspect
import sys
from dataclasses import dataclass
from pprint import pformat
from typing import List, Generic, Mapping, Union, Callable, TypeVar, Tuple, Set, Any, Dict

import makefun
from loguru import logger
from makefun import create_function
from returns.maybe import Maybe, Nothing

T, U = TypeVar("T"), TypeVar("U")

A = TypeVar("A")
B = TypeVar("B")


@dataclass
class FrameInfo:
    filename: str
    line_number: int
    function_name: str
    sources: List[str]
    line_idx_in_sources: int


def get_frame_info(stack_idx) -> Union[None, FrameInfo]:
    try:
        return FrameInfo(*inspect.getframeinfo(inspect.stack(0)[stack_idx][0]))
    except Exception as e:
        return None


def partialclass(name, cls, *args, **kwds):
    """
    copied from https://stackoverflow.com/questions/38911146/python-equivalent-of-functools-partial-for-a-class-constructor
    :param name:
    :param cls:
    :param args:
    :param kwds:
    :return:
    """
    new_cls = type(name, (cls,), {
        '__init__': functools.partialmethod(cls.__init__, *args, **kwds)
    })

    # The following is copied nearly ad verbatim from `namedtuple's` source.
    """
    # For pickling to work, the __module__ variable needs to be set to the frame
    # where the named tuple is created.  Bypass this step in enviroments where
    # sys._getframe is not defined (Jython for example) or sys._getframe is not
    # defined for arguments greater than 0 (IronPython).
    """
    try:
        new_cls.__module__ = sys._getframe(1).f_globals.get('__name__', '__main__')
    except (AttributeError, ValueError):
        pass

    return new_cls


class Injected(Generic[T], metaclass=abc.ABCMeta):
    """
    this class is actually an abstraction of fucntion partial application.
    """

    @staticmethod
    def partial(target_function: Callable, **injection_targets: "Injected") -> "Injected[Callable]":
        """
        use this to partially inject specified params, and leave the other parameters to be provided after injection is resolved
        :param target_function: Callable
        :param injection_targets: specific parameters to make injected automatically
        :return: Injected[Callable[(params which were not specified in injection_targets)=>Any]]
        """
        # how can I partially apply class constructor?
        argspec = inspect.getfullargspec(target_function)
        remaining_arg_names = argspec.args
        if "self" in remaining_arg_names:
            remaining_arg_names.remove("self")
        # logger.info(f"partially applying {injection_targets}")
        # logger.info(f"original args:{remaining_arg_names}")

        for injected in injection_targets.keys():
            remaining_arg_names.remove(injected)

        def makefun_impl(kwargs):
            # logger.info(f"partial injection :{pformat(kwargs)}")

            def inner(*_args):
                # user calls with both args or kwargs so we need to handle both.
                assert len(_args) == len(remaining_arg_names), \
                    f"partially applied injected function is missing some of positional args! {remaining_arg_names} for {_args}"
                call_kwargs = dict(zip(remaining_arg_names, _args))
                # logger.info(f"partial injection call :{pformat(call_kwargs)}")
                full_kwargs = {**kwargs, **call_kwargs}
                return target_function(**full_kwargs)

            return inner

        injected_kwargs = Injected.dict(**injection_targets)
        injected_factory = Injected.bind(makefun_impl, kwargs=injected_kwargs)
        return injected_factory

    @staticmethod
    def inject_except(target_function, *whitelist: str) -> "Injected[Callable]":
        """
        :param target_function:
        :param whitelist: name of arguments which should not be injected by DI.
        :return: Injected[Callable[(whitelisted args)=>Any]]
        """
        argspec = inspect.getfullargspec(target_function)
        args_to_be_injected = [a for a in argspec.args if a not in whitelist and a != "self"]
        return Injected.partial(target_function, **{item: Injected.by_name(item) for item in args_to_be_injected})

    @staticmethod
    def bind(_target_function_, **kwargs_mapping: Union[str, type, Callable, "Injected"]) -> "Injected":
        if isinstance(_target_function_, Injected):
            _target_function_ = _target_function_.get_provider()
        return InjectedFunction(
            target_function=_target_function_,
            kwargs_mapping=kwargs_mapping
        )

    @staticmethod
    def direct(_target_function, **kwargs) -> "Injected":
        """
        uses Injected.pure by default unless the parameter is an instance of Injected.
        :param _target_function:
        :param kwargs:
        :return:
        """
        en_injected = {k: Injected.pure(v) for k, v in kwargs.items() if not isinstance(v, Injected)}
        already_injected = {k: v for k, v in kwargs.items() if isinstance(v, Injected)}
        return Injected.bind(_target_function, **en_injected, **already_injected)

    def _faster_get_fname(self):
        try:
            frame = sys._getframe().f_back.f_back.f_back.f_back
            mod = frame.f_globals["__name__"]
            name = frame.f_lineno
            return f"{mod.replace('.', '_')}_L_{name}".replace("<", "__").replace(">", "__")
        except Exception as e:
            from loguru import logger
            logger.warning(f"failed to get name of the injected location.")
            return f"__unknown_module__maybe_due_to_pickling__"

    def __init__(self):
        self.fname = self._faster_get_fname()

    @abc.abstractmethod
    def dependencies(self) -> Set[str]:
        pass

    def get_signature(self):
        sig = f"""{self.fname}({",".join(self.dependencies())})"""
        # logger.warning(sig)
        return sig

    @abc.abstractmethod
    def get_provider(self):
        """
        :return: a provider
        """

    def map(self, f: Callable[[T], U]) -> 'Injected[U]':
        return MappedInjected(4, self, f)

    @staticmethod
    def from_impl(impl: Callable, dependencies: Set[str]):
        return GeneratedInjected(impl, dependencies)

    @staticmethod
    def pure(value):
        return InjectedPure(value)

    @staticmethod
    def by_name(name: str):
        return InjectedByName(name, )

    def zip(self, other: "Injected[U]") -> "Injected[Tuple[T,U]]":
        return ZippedInjected(self, other, )

    @staticmethod
    def mzip(*srcs: "Injected"):
        return MZippedInjected(*srcs)

    # this is ap of applicative functor.
    def apply_injected_function(self, other: "Injected[Callable[[T],U]]") -> "Injected[U]":
        return self.zip(other).map(
            lambda t: t[1](t[0])
        )

    @staticmethod
    def dict(**kwargs: "Injected") -> "Injected[Dict]":
        keys = list(kwargs.keys())
        return Injected.mzip(*[kwargs[k] for k in keys]).map(lambda t: {k: v for k, v in zip(keys, t)})

    @property
    def proxy(self):
        """use this to modify injected variables freely without map.
        call eval() at the end to finish modification
        """
        from pinject_design.di.app_injected import injected_proxy
        return injected_proxy(self)


class GeneratedInjected(Injected):
    """creates Injected from dependencies and funct(**kwargs) signature"""

    def __init__(self, impl: Callable, dependencies: Set[str]):
        super().__init__()
        self.impl = impl
        self._dependencies = dependencies

    def dependencies(self) -> Set[str]:
        return self._dependencies

    def get_provider(self):
        return create_function(self.get_signature(), func_impl=self.impl)


class MappedInjected(Injected):
    src: Injected[T]
    f: Callable[[T], U]

    def __init__(self, stack, src, f):
        super(MappedInjected, self).__init__()
        self.src = src
        self.f = f

    def dependencies(self) -> Set[str]:
        return self.src.dependencies()

    def get_provider(self):
        def impl(**kwargs):
            assert self.dependencies() == set(
                kwargs.keys())  # this is fine but get_provider returns wrong signatured func
            tmp = self.src.get_provider()(**kwargs)
            return self.f(tmp)

        return create_function(self.get_signature(), func_impl=impl)


class MapWithExtras(Injected):
    src: Injected[T]
    f: Callable[[T, Any], U]
    extras: Set[str]

    def __init__(self, stack, src, f, extras: Set[str]):
        super(MappedInjected, self).__init__(stack)
        self.src = src
        self.f = f
        self.extras = extras

    def dependencies(self) -> Set[str]:
        return self.src.dependencies() | self.extras

    def get_provider(self):
        def impl(**kwargs):
            src_deps = {k: kwargs[k] for k in self.src.dependencies()}
            extras = {k: kwargs[k] for k in self.extras}
            tmp = self.src.get_provider()(**src_deps)
            return self.f(tmp, **extras)

        return create_function(self.get_signature(), func_impl=impl)


def extract_dependency_including_self(f: Union[type, Callable]):
    if isinstance(f, type):  # it's a constructor and we must use __init__ for backward compatibility.
        argspec = inspect.getfullargspec(f.__init__)
        return set(argspec.args)
    elif isinstance(f, Callable):
        argspec = inspect.getfullargspec(f)
        return set(argspec.args)
    else:
        raise RuntimeError(f"input:{f} is not either type or Callable")


def extract_dependency(dep: Union[str, type, Callable, Injected]) -> Set[str]:
    if isinstance(dep, str):
        return {dep}
    elif isinstance(dep, type):  # it's a constructor and we must use __init__ for backward compatibility.
        argspec = inspect.getfullargspec(dep.__init__)
        return set(argspec.args) - {'self'}
    elif isinstance(dep, Callable):
        try:
            argspec = inspect.getfullargspec(dep)
        except Exception as e:
            raise e

        return set(argspec.args) - {'self'}
    elif isinstance(dep, Injected):
        return dep.dependencies()
    else:
        raise RuntimeError(f"dep must be either str/type/Callable/Injected. got {type(dep)}")


def solve_injection(dep: Union[str, type, Callable, Injected], kwargs: dict):
    if isinstance(dep, str):
        return kwargs[dep]
    elif isinstance(dep, (type, Callable)):
        return dep(**{k: kwargs[k] for k in extract_dependency(dep)})
    elif isinstance(dep, Injected):
        return solve_injection(dep.get_provider(), kwargs)
    else:
        raise RuntimeError(f"dep must be one of str/type/Callable/Injected. got {type(dep)}")


def combine_image_store(a, b):
    # do anything
    return a + b


def assert_kwargs_type(v):
    if isinstance(v, str):
        return
    if isinstance(v, type):
        return
    if isinstance(v, Callable):
        return
    if isinstance(v, Injected):
        return
    else:
        raise TypeError(f"{type(v)} is not any of [str,type,Callable,Injected]")


class InjectedFunction(Injected[T]):
    # since the behavior differs in classes extending Generic[T]
    def __init__(self,
                 target_function: Callable,
                 kwargs_mapping: Mapping[str, Union[str, type, Callable, Injected]]
                 ):
        super().__init__()
        assert callable(target_function)
        self.target_function = target_function
        self.kwargs_mapping = kwargs_mapping
        for k, v in self.kwargs_mapping.items():
            assert v is not None, f"injected got None binding for key:{k}"
            assert_kwargs_type(v)

        org_deps = extract_dependency(self.target_function)
        # logger.info(f"tgt:{target_function} original dependency:{org_deps}")
        missings = {d for d in org_deps if d not in self.kwargs_mapping}
        # logger.info(f"now missing {missings}")
        # logger.warning(f"created InjectedFunction:{inspect.signature(target_function)}")
        # assert "self" not in inspect.signature(target_function).parameters
        self.missings = missings

    def override_mapping(self, **kwargs: Union[str, type, Callable, Injected]):
        return InjectedFunction(self.target_function, {**self.kwargs_mapping, **kwargs})

    def get_provider(self):
        signature = self.get_signature()

        def impl(**kwargs):
            deps = dict()
            for mdep in self.missings:
                deps[mdep] = solve_injection(mdep, kwargs)
            for k, dep in self.kwargs_mapping.items():
                deps[k] = solve_injection(dep, kwargs)
            # logger.info(f"calling function:{self.target_function.__name__}{inspect.signature(self.target_function)}")
            return self.target_function(**deps)

        # you have to add a prefix 'provider'""
        return create_function(func_signature=signature, func_impl=impl)

    def dependencies(self) -> Set[str]:
        # ahhhh this recursively demands for injection.
        # we need to distinguish what and what not to recursively inject
        res = set()
        for mdep in self.missings:
            d = extract_dependency(mdep)
            res |= d
            # logger.info(f"deps of missing:{d}")
        for k, dep in self.kwargs_mapping.items():
            d = extract_dependency(dep)
            res |= d
            # logger.info(f"deps of dependency({k}):{d}")
        return res

    # def __str__(self):
    #    return f"""InjectedFunction(target={self.target_function},kwargs_mapping={self.kwargs_mapping})"""


class InjectedPure(Injected[T]):
    __match_args__ = ("value",)

    def __init__(self, value):
        super().__init__()
        self.value = value

    def dependencies(self) -> Set[str]:
        return set()

    def get_provider(self):
        return create_function(func_signature=self.get_signature(), func_impl=lambda: self.value)

    def __str__(self):
        return f"Pure({self.value})"
    def __repr__(self):
        return str(self)


class InjectedByName(Injected[T]):
    def __init__(self, name):
        super().__init__()
        self.name = name

    def dependencies(self) -> Set[str]:
        return {self.name}

    def get_provider(self):
        return create_function(func_signature=self.get_signature(), func_impl=lambda **kwargs: kwargs[self.name])


class ZippedInjected(Injected[Tuple[A, B]]):
    def __init__(self, a: Injected[A], b: Injected[B]):
        super().__init__()
        self.a = a
        self.b = b

    def dependencies(self) -> Set[str]:
        return set(self.a.dependencies() | self.b.dependencies())

    def get_provider(self):
        def impl(**kwargs):  # can we pickle this though?
            a_kwargs = {k: kwargs[k] for k in self.a.dependencies()}
            b_kwargs = {k: kwargs[k] for k in self.b.dependencies()}
            a = self.a.get_provider()(**a_kwargs)
            b = self.b.get_provider()(**b_kwargs)
            return a, b

        signature = self.get_signature()
        # logger.info(f"created signature:{signature} for ZippedInjected")
        return create_function(func_signature=signature, func_impl=impl)


class MZippedInjected(Injected):
    def __init__(self, *srcs: Injected):
        super().__init__()
        self.srcs = srcs
        assert all(isinstance(s,Injected) for s in srcs),srcs

    def dependencies(self) -> Set[str]:
        res = set()
        for s in self.srcs:
            res |= s.dependencies()
        return res

    def get_provider(self):
        def impl(**kwargs):  # can we pickle this though?
            each_kwargs = [{k: kwargs[k] for k in s.dependencies()} for s in self.srcs]
            res = []
            for s in self.srcs:
                r = s.get_provider()(**{k: kwargs[k] for k in s.dependencies()})
                res.append(r)
            return tuple(res)

        signature = self.get_signature()
        from loguru import logger
        logger.info(f"created signature:{signature} for MZippedInjected")
        return create_function(func_signature=signature, func_impl=impl)


def _injected_factory(**targets: Injected):
    def _impl(f):
        return Injected.partial(f, **targets)

    return _impl


def injected_factory(f):
    """
    any args starting with "_" is considered to be injected.
    :param f:
    :return:
    """
    sig: inspect.Signature = inspect.signature(f)
    tgts = dict()
    for k in sig.parameters.keys():
        if k.startswith("_"):
            tgts[k] = Injected.by_name(k[1:])
    return _injected_factory(**tgts)(f)
