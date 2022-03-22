import abc
import functools
import inspect
import sys
from dataclasses import dataclass
from typing import List, Generic, Mapping, Union, Callable, TypeVar, Tuple, Set, Any

import makefun
from loguru import logger
from makefun import create_function

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
    what I want to achieve is ..
    to define a function that can accept injected[T]s to return injected[X]
    I only want to define a function that converts it.
    so given a function we want to lift that function to Injected Function
    so, define a function and convert it with mappings
    """

    @staticmethod
    def partial(target_function: Callable, **manual_injections) -> "Injected[Callable]":
        """
        use this to partially inject specified params, and leave the other parameters to be provided after injection is resolved
        :param target_function: Callable
        :param manual_injections: specific parameters to inject
        :return:
        """
        # how can I partially apply class constructor?
        if isinstance(target_function, type):
            partial = functools.partial(partialclass, target_function.__name__ + "Applied")
        else:
            partial = functools.partial

        def _impl_for_injection(**kwargs):
            return partial(target_function, **kwargs)

        sig = f"""{target_function.__name__}_provider({",".join(manual_injections.keys())})"""
        func = makefun.create_function(sig, _impl_for_injection)
        return Injected.bind(func)

    @staticmethod
    def bind(_target_function_, **kwargs_mapping: Union[str, type, Callable, "Injected"]) -> "Injected":
        return InjectedFunction(
            target_function=_target_function_,
            kwargs_mapping=kwargs_mapping
        )

    def _faster_get_fname(self):
        frame = sys._getframe().f_back.f_back.f_back.f_back
        mod = frame.f_globals["__name__"]
        name = frame.f_lineno
        return f"{mod.replace('.', '_')}_L_{name}"

    def __init__(self, init_stack):
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
        return GeneratedInjected(impl, dependencies, init_stack=4)

    @staticmethod
    def pure(value):
        return InjectedPure(value, init_stack=4)

    @staticmethod
    def by_name(name: str):
        return InjectedByName(name, init_stack=4)

    def zip(self, other: "Injected[U]") -> "Injected[Tuple[T,U]]":
        return ZippedInjected(self, other, init_stack=4)

    @staticmethod
    def mzip(*srcs: "Injected"):
        return MZippedInjected(4, *srcs)

    # this is ap of applicative functor.
    def apply_injected_function(self, other: "Injected[Callable[[T],U]]") -> "Injected[U]":
        return self.zip(other).map(
            lambda t: t[1](t[0])
        )


class GeneratedInjected(Injected):
    """creates Injected from dependencies and funct(**kwargs) signature"""

    def __init__(self, impl: Callable, dependencies: Set[str], init_stack):
        super().__init__(init_stack)
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
        super(MappedInjected, self).__init__(stack)
        self.src = src
        self.f = f

    def dependencies(self) -> Set[str]:
        return self.src.dependencies()

    def get_provider(self):
        def impl(**kwargs):
            tmp = self.src.get_provider()(**kwargs)
            return self.f(tmp)

        return create_function(self.get_signature(), func_impl=impl)

class MapWithExtras(Injected):
    src:Injected[T]
    f:Callable[[T,Any],U]
    extras:Set[str]

    def __init__(self, stack, src, f,extras:Set[str]):
        super(MappedInjected, self).__init__(stack)
        self.src = src
        self.f = f
        self.extras=extras

    def dependencies(self) -> Set[str]:
        return self.src.dependencies() | self.extras

    def get_provider(self):
        def impl(**kwargs):
            src_deps = {k:kwargs[k] for k in self.src.dependencies()}
            extras = {k:kwargs[k] for k in self.extras}
            tmp = self.src.get_provider()(**src_deps)
            return self.f(tmp,**extras)

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
        argspec = inspect.getfullargspec(dep)
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
        super().__init__(init_stack=4)
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

    def get_provider(self):
        signature = self.get_signature()

        def impl(**kwargs):
            deps = dict()
            for mdep in self.missings:
                deps[mdep] = solve_injection(mdep, kwargs)
            for k, dep in self.kwargs_mapping.items():
                deps[k] = solve_injection(dep, kwargs)
            #logger.info(f"calling function:{self.target_function.__name__}{inspect.signature(self.target_function)}")
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

    def __str__(self):
        return f"""InjectedFunction(target={self.target_function},kwargs_mapping={self.kwargs_mapping})"""


class InjectedPure(Injected[T]):
    def __init__(self, value, init_stack):
        super().__init__(init_stack)
        self.value = value

    def dependencies(self) -> Set[str]:
        return set()

    def get_provider(self):
        return create_function(func_signature=self.get_signature(), func_impl=lambda: self.value)


class InjectedByName(Injected[T]):
    def __init__(self, name, init_stack):
        super().__init__(init_stack)
        self.name = name

    def dependencies(self) -> Set[str]:
        return set(self.name)

    def get_provider(self):
        return create_function(func_signature=self.get_signature(), func_impl=lambda v: v)


class ZippedInjected(Injected[Tuple[A, B]]):
    def __init__(self, a: Injected[A], b: Injected[B], init_stack):
        super().__init__(init_stack)
        self.a = a
        self.b = b

    def dependencies(self) -> Set[str]:
        return set(self.a.dependencies() | self.b.dependencies())

    def get_provider(self):
        def impl(**kwargs):  # can we pickle this though?
            logger.info(f"providing from ZippedInjected!:{kwargs}")
            logger.info(f"a:{self.a}")
            logger.info(f"b:{self.b}")
            a_kwargs = {k: kwargs[k] for k in self.a.dependencies()}
            b_kwargs = {k: kwargs[k] for k in self.b.dependencies()}
            # embed()
            a = self.a.get_provider()(**a_kwargs)
            logger.info(f"a:{a}")
            b = self.b.get_provider()(**b_kwargs)
            logger.info(f"b:{b}")
            logger.info((a, b))
            return a, b

        signature = self.get_signature()
        logger.info(f"created signature:{signature} for ZippedInjected")
        return create_function(func_signature=signature, func_impl=impl)


class MZippedInjected(Injected):
    def __init__(self, init_stack, *srcs: Injected):
        super().__init__(init_stack)
        self.srcs = srcs

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
        logger.info(f"created signature:{signature} for MZippedInjected")
        return create_function(func_signature=signature, func_impl=impl)
