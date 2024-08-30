import abc
import asyncio
import functools
import hashlib
import inspect
import sys
from copy import copy
from dataclasses import dataclass, field
from typing import List, Generic, Union, Callable, TypeVar, Tuple, Set, Dict, Any, Awaitable, Optional

import cloudpickle
from frozendict import frozendict
from makefun import create_function
from returns.result import safe

from pinjected.compatibility.task_group import TaskGroup
from pinjected.di.args_modifier import ArgsModifier, KeepArgsPure
from pinjected.di.injected_analysis import get_instance_origin
from pinjected.di.proxiable import DelegatedVar

T, U = TypeVar("T"), TypeVar("U")

A = TypeVar("A")
B = TypeVar("B")

INJECTED_CONTEXT = frozendict()
"""
This is a global context for injected.
This context is copied on the creation time of an Injected.
This is useful for passing the context to the Injected instance.
However, be careful that you pass correct context.
For example, whe using with DelegatedVar, do keep the context in DelegatedVar and then pass the context to InjectedInstance at the end.
Also, if beware that the context will not be propagated for operations.
examples:
with InjectedContext({"a":1}):
    a = Injected.by_name("a")
    b = a.map(lambda x:x+1) # here b will have the context {"a":1}, so it will return 2
b = a.map(lambda x:x+1) # here the map function will not have the context {"a":1}, so it will return undefined.
to mitigate this, we need modify all the operators to propagate the parent context, which is not easy.
Okey, so let's implement this and be aware that the map function will erase it.
So the use needs to be careful to add context at the very end, for running purposes.
"""


@dataclass
class FrameInfo:
    original_frame: object
    trc: "Traceback"
    filename: str
    line_number: int
    function_name: str
    sources: List[str]
    line_idx_in_sources: int


def get_frame_info(stack_idx) -> Union[None, FrameInfo]:
    try:
        original_trc = inspect.stack(0)[stack_idx][0]
        trc: "Traceback" = inspect.getframeinfo(original_trc)
        return FrameInfo(original_trc, trc, *trc)
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


@dataclass
class ParamInfo:
    params_to_fill: Dict  # = tgt_sig.parameters
    params_state: Dict  # = dict()
    vargs: List = field(default_factory=list)  # = []
    kwargs: Dict = field(default_factory=dict)  # = dict()
    # the problem is we may or may not have vargs and kwargs...


"""
Semantics of an Injected:
For Injected[T], upon resolving T, all dependencies are resolved for T.
So, if T is a Callable, then any dependencies are resolved before calling it.

However, for Lazy Injected thing, we want the dependencies to be resolved inside the function.
This is because,, for asyncio stuff, the dependencies end their life after asyncio.run has finished for resolving the dependencies.
For asyncio thing to work, we need to keep asyncio.run unfinished and only run at the top level for once.
So, the solutions are:
1. make async functions resolve dependencies on demand.
2. make run_injected async and call asyncio.run only once.

Let's got with 2nd option.
"""


class PicklableInjectedFunction:
    def __init__(self,
                 src: callable,
                 __doc__,
                 __name__,
                 __skeleton__,
                 __is_async__
                 ):
        self.src = src
        self.__doc__ = __doc__
        self.__name__ = __name__
        self.__skeleton__ = __skeleton__
        self.__is_async__ = __is_async__

    def __getstate__(self):
        return cloudpickle.dumps(
            (self.src, self.__doc__, self.__name__, self.__skeleton__, self.__is_async__)
        )

    def __setstate__(self, state):
        self.src, self.__doc__, self.__name__, self.__skeleton__, self.__is_async__ = cloudpickle.loads(state)

    def __call__(self, *args, **kwargs):
        return self.src(*args, **kwargs)


class Injected(Generic[T], metaclass=abc.ABCMeta):
    """
    The ``Injected`` class represents a sophisticated dependency injection mechanism in Python.
    It encapsulates an object that requires certain dependencies to be resolved. The class maintains
    a set of dependencies necessary for the object's creation and utilizes a provider function that
    generates the desired variable with its dependencies satisfied.

    Basic Usage:
    ------------

    .. code-block:: python

        from pinjected.di.util import Injected
        from pinjected import Design

        def provide_ab(a:int, b:int) -> int:
            return a + b

        # The bind method creates an Injected object from a provider function, using the function's
        # arguments as dependencies.
        injected: Injected[int] = Injected.bind(provide_ab)

        design = EmptyDesign.bind_instance(a=1, b=2)
        assert design.to_graph()[injected] == 3

    Advanced Features:
    ------------------

    **Composition:**

    ``Injected`` instances can be manipulated and combined in several ways to build complex dependency structures.

    1. **map**: Transform the result of an ``Injected`` instance.

        .. code-block:: python

            from pinjected.di.util import Injected, instances
            from pinjected import Design

            design: Design = instances(a=1)  # Shortcut for binding instances
            a: Injected[int] = Injected.by_name('a')
            b: Injected[int] = a.map(lambda x: x + 1)  # b is now a + 1

            g = design.to_graph()
            assert g[a] + 1 == g[b]

    2. **zip/mzip**: Combine multiple ``Injected`` instances.

        .. code-block:: python

            from pinjected.di.util import Injected
            from pinjected import Design

            design = EmptyDesign.bind_instance(a=1, b=2)
            g = design.to_graph()

            a = Injected.by_name('a')
            b = Injected.by_name('b')
            c = a.map(lambda x: x + 2)
            abc = Injected.mzip(a, b, c)  # Combine more than two Injected instances
            ab_zip = Injected.zip(a, b)   # Standard zip for two Injected instances

            assert g[abc] == (1, 2, 3)
            assert g[ab_zip] == (1, 2)

    3. **dict/list**: Create a dictionary or list from multiple ``Injected`` instances.

        .. code-block:: python

            from pinjected.di.util import Injected, instances

            design = instances(a=1, b=2)
            a = Injected.by_name('a')
            b = Injected.by_name('b')
            c = a.map(lambda x: x + 2)

            injected_dict: Injected[dict] = Injected.dict(a=a, b=b, c=c)  # Creates {'a':1, 'b':2, 'c':3}
            injected_list: Injected[list] = Injected.list(a, b, c)  # Creates [1, 2, 3]

    These composition tools enhance the flexibility of dependency injection, enabling more complex
    and varied structures to suit diverse programming needs. By allowing transformations and combinations
    of ``Injected`` instances, they provide powerful ways to manage and utilize dependencies within
    your applications.
    """

    @staticmethod
    def inject_partially(original_function: Callable, **injection_targets: "Injected") -> "Injected[Callable]":
        from pinjected.di.partially_injected import Partial
        modifier = Injected._get_args_keeper(injection_targets, inspect.signature(original_function))
        # TODO move this modifier to @injected decorator.
        return Partial(original_function, injection_targets, modifier)

    @staticmethod
    def _get_args_keeper(injection_targets, original_sig):
        original_args_with_Injected = []
        for k, v in original_sig.parameters.items():
            if k not in injection_targets:
                if v.annotation == Injected:
                    original_args_with_Injected.append(k)
        remaining_params = [p for name, p in original_sig.parameters.items() if name not in injection_targets]
        remaining_signature: inspect.Signature = original_sig.replace(parameters=remaining_params)
        modifier = KeepArgsPure(
            signature=remaining_signature,
            targets=set(original_args_with_Injected)
        )
        return modifier

    @staticmethod
    def inject_except(target_function, *whitelist: str) -> "Injected[Callable]":
        """
        :param target_function:
        :param whitelist: name of arguments which should not be injected by DI.
        :return: Injected[Callable[(whitelisted args)=>Any]]
        """
        argspec = inspect.getfullargspec(target_function)
        args_to_be_injected = [a for a in argspec.args if a not in whitelist and a != "self"]
        return Injected.inject_partially(target_function,
                                         **{item: Injected.by_name(item) for item in args_to_be_injected})

    @staticmethod
    def bind(_target_function_, _dynamic_dependencies_: set[str] = None,
             **kwargs_mapping: Union[str, type, Callable, "Injected"]) -> "InjectedFunction":
        assert not isinstance(_target_function_, Injected), f"target_function should not be an instance of Injected"
        # if isinstance(_target_function_, Injected):
        #     _target_function_ = _target_function_.get_provider()
        assert callable(_target_function_), f"target_function should be callable, but got {_target_function_}"
        if not inspect.iscoroutinefunction(_target_function_):
            # we need to keep the function signature

            async def _a_target_function(*args, **kwargs):
                return _target_function_(*args, **kwargs)

            _a_target_function.__signature__ = inspect.signature(_target_function_)

            async_target_function = _a_target_function
            async_target_function.__original_code__ = safe(inspect.getsource)(_target_function_).value_or(
                "not available")
        else:
            async_target_function = _target_function_
        res = InjectedFunction(
            original_function=_target_function_,
            target_function=async_target_function,
            kwargs_mapping=kwargs_mapping,
            dynamic_dependencies=_dynamic_dependencies_
        )
        return res

    @staticmethod
    def direct(_target_function, **kwargs) -> "Injected":
        """
        uses Injected.pure by default unless the parameter is an instance of Injected.
        :param _target_function:
        :param kwargs:
        :return:
        """
        en_injected = {k: Injected.pure(v) for k, v in kwargs.items() if not isinstance(v, (Injected, DelegatedVar))}
        already_injected = {k: v for k, v in kwargs.items() if isinstance(v, (Injected, DelegatedVar))}
        return Injected.bind(_target_function, **en_injected, **already_injected)

    def _faster_get_fname(self):

        try:
            frame = sys._getframe().f_back.f_back.f_back.f_back
            mod = frame.f_globals["__name__"]
            name = frame.f_lineno
            return f"{mod.replace('.', '_')}_L_{name}".replace("<", "__").replace(">", "__")
        except Exception as e:
            # from loguru import logger
            # logger.warning(f"failed to get name of the injected location.")
            return f"__unknown_module__maybe_due_to_pickling__"

    def __init__(self):
        self.fname = self._faster_get_fname()

    @staticmethod
    def partial(f: 'Injected[Callable]', *args: "Injected", **kwargs: "Injected"):
        """
        applies partial application to the given function.
        """

        # ah this loses the info about coroutine..
        def make_partially_applied(t):
            f, args, kwargs = t
            func = functools.partial(f, *args, **kwargs)
            func.__name__ = getattr(f, "__name__", "<unknown>")
            return func

        injected_args = Injected.tuple(*args)
        injected_kwargs = Injected.dict(**kwargs)

        applied_func = Injected.mzip(f, injected_args, injected_kwargs).map(make_partially_applied)
        # how can I keep __is_async_function__ ?
        pf = PartialInjectedFunction(
            applied_func
        )
        if hasattr(f, "__is_async_function__"):
            pf.__is_async_function__ = f.__is_async_function__  # this maybe not used
            applied_func.__is_async_function__ = f.__is_async_function__  # this is important
        return pf

    @abc.abstractmethod
    def dependencies(self) -> Set[str]:
        pass

    @abc.abstractmethod
    def dynamic_dependencies(self) -> Set[str]:
        """
        :return: a set of dependencies which are not statically known. mainly used for analysis.

        use this to express an injected that conditionally depends on something, such as caches.
        """
        raise NotImplementedError

    @property
    def complete_dependencies(self) -> Set[str]:
        return self.dependencies() | self.dynamic_dependencies()

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
        # return MappedInjected(self, f)
        if not inspect.iscoroutinefunction(f):
            #@functools.wraps(f) #wraps breaks built-in function to be unpicklable...
            async def async_f(*args, **kwargs):
                return f(*args, **kwargs)

            # from loguru import logger
            # logger.warning(f"converting {f} to async function")

            new_f = async_f
        else:
            new_f = f
        return MappedInjected(self, new_f, original_mapper=f)

    def from_impl(impl: Callable, dependencies: Set[str]):
        return GeneratedInjected(impl, dependencies)

    def _faster_get_metadata(self):
        # logger.info(f"faster_get_metadata for Injected.pure")
        try:
            frame = sys._getframe().f_back.f_back
            mod = frame.f_globals["__name__"]
            name = frame.f_code.co_filename
            # return f"{mod.replace('.', '_')}_L_{name}".replace("<", "__").replace(">", "__")
            return mod, name
        except Exception as e:
            # from loguru import logger
            from loguru import logger
            logger.warning(f"failed to get name of the injected location, due to {e}")
            return f"__unknown_module__maybe_due_to_pickling__", "unknown_location"

    @staticmethod
    def pure(value):
        res = InjectedPure(value)
        # I need to set the file that called this function.
        # res.__definition_frame__ = get_frame_info(2)
        # fi = get_frame_info(2)
        res.__definition_module__, res.__original_file__ = res._faster_get_metadata()
        # res.__definition_module__ = fi.original_frame.f_globals["__name__"]
        # res.__original_file__ = fi.filename
        return res

    @staticmethod
    def by_name(name: str):
        return InjectedByName(name, )

    def zip(self, other: "Injected[U]") -> "Injected[Tuple[T,U]]":
        return Injected.mzip(self, other)

    @staticmethod
    def mzip(*srcs: "Injected"):
        srcs = [Injected.wrap_injected_if_not(s) for s in srcs]
        return MZippedInjected(*srcs)

    @staticmethod
    def tuple(*srcs: "Injected"):
        # from pinjected.di.static_method_impl import ituple
        # srcs = [Injected.wrap_injected_if_not(s) for s in srcs]
        # return Injected.mzip(*srcs).map(lambda t: tuple(t))
        return Injected.pure(_en_tuple).proxy(*srcs)
        # return ituple(*srcs)

    @staticmethod
    def wrap_injected_if_not(tgt: Union["Injected", DelegatedVar, Any]):
        match tgt:
            case Injected():
                return tgt
            case DelegatedVar():
                return tgt.eval()
            case _:
                return Injected.pure(tgt)

    @staticmethod
    def list(*srcs: Union["Injected", "DelegatedVar"]):
        # from pinjected.di.static_method_impl import ilist
        # return Injected.mzip(*srcs).map(list)
        return Injected.pure(_en_list).proxy(*srcs)
        # return ilist(*srcs)

    @staticmethod
    def async_gather(*srcs: "Injected[Awaitable]"):
        def gather(coros):
            async def wait():
                return await asyncio.gather(*coros)

            return asyncio.run(wait())

        return Injected.mzip(*srcs).map(gather)

    @staticmethod
    def map_elements(f: "Injected[Callable]", elements: "Injected[Iterable]") -> "Injected[Iterable]":
        """
        # for (
        #     f <- f,
        #     elements <- elements
        #     ) yield map(f,elements)

        :param f:
        :param elements:
        :return:

        """
        return Injected.mzip(
            f, elements
        ).map(lambda x: map(x[0], x[1]))

    # this is ap of applicative functor.
    def apply_injected_function(self, other: "Injected[Callable[[T],U]]") -> "Injected[U]":
        return self.zip(other).map(
            lambda t: t[1](t[0])
        )

    def and_then_injected(self, other: "Injected[Callable[[T],U]]") -> "Injected[Callable[[Any],U]]":
        return self.zip(other).map(
            lambda t: lambda *args, **kwargs: t[1](t[0](*args, **kwargs))
        )

    @staticmethod
    def dict(**kwargs: "Injected") -> "Injected[Dict]":
        # from pinjected.di.static_method_impl import idict
        # return idict(**kwargs)
        # raise RuntimeError("disabled")
        # keys = list(kwargs.keys())
        # return Injected.mzip(*[kwargs[k] for k in keys]).map(lambda t: {k: v for k, v in zip(keys, t)})

        return Injected.pure(dict).proxy(**kwargs)
        # return DictInjected(**kwargs)

    @property
    def proxy(self) -> DelegatedVar:
        """use this to modify injected variables freely without map.
        call eval() at the end to finish modification
        # it seems this thing is preventing from pickling?
        """
        from pinjected.di.app_injected import injected_proxy
        return injected_proxy(self)

    @staticmethod
    def ensure_injected(data: Union["Injected", DelegatedVar]):
        match data:
            case DelegatedVar():
                # this eval() causes the proxy to be unpicklable. but we can't tell why.
                return Injected.ensure_injected(data.eval())
            case Injected():
                return data
            case func if callable(func):
                return Injected.bind(func)
            case _:
                raise RuntimeError(f"not an injected object: {data},type(data)={type(data)}")

    def __add__(self, other: "Injected"):
        match other:
            case int() | float() | str():
                other = Injected.pure(other)
        other = Injected.ensure_injected(other)
        return (self.proxy + other).eval()
        # return self.zip(other).map(lambda t: t[0] + t[1])

    def __getitem__(self, item):
        # return self.map(lambda x: x[item])
        return self.proxy[item]

    def desync(self):
        async def impl(awaitable):
            return await awaitable

        return self.map(lambda coroutine: asyncio.run(impl(coroutine)))

    @staticmethod
    def dynamic(tgt:str):
        async def provide_from_resolver(__resolver__):
            return await __resolver__[tgt]
        return Injected.bind(
            provide_from_resolver,
            _dynamic_dependencies_={tgt}
        )

    def add_dynamic_dependencies(self, *deps: Union[str, set[str]]):
        deps_set = set()
        for item in deps:
            match item:
                case str():
                    deps_set.add(item)
                case set():
                    deps_set |= item
                case [*items]:
                    for i in items:
                        assert isinstance(i, str), f"item should be string, but got {i}"
                        deps_set.add(i)
                case _:
                    raise RuntimeError(f"item should be string or set of string, but got {item}")
        return InjectedWithDynamicDependencies(self, deps_set)

    def __len__(self):
        return self.map(len)

    # Implementing these might end up with pickling issues. due to recursive getattr..?
    # def __call__(self, *args, **kwargs):
    #     return self.proxy(*args, **kwargs)
    #
    # def __getitem__(self, item):
    #     return self.proxy[item]

    @staticmethod
    def conditional(condition: "Injected[bool]", true_case: "Injected", false_case: "Injected"):
        return ConditionalInjected(condition, true_case, false_case)

    @staticmethod
    def procedure(*targets: "Injected"):
        """
        Runs the targets in order, and returns the last one.
        This is useful for running injecteds which performs side effects.
        :param targets:
        :return:
        """
        if not targets:
            return Injected.pure(None)
        queue = list(targets[1:])
        top = targets[0]
        while queue:
            next = queue.pop(0)
            top = Injected.tuple(top, next)
        return top[1]

    @staticmethod
    def conditional_preparation(
            condition: "Injected[bool]",
            preparation: "Injected",
            utilization: "Injected"
    ):
        return Injected.conditional(
            condition,
            utilization,
            Injected.procedure(
                preparation,
                utilization
            )
        )

    @abc.abstractmethod
    def __repr_expr__(self):
        raise NotImplementedError()


@dataclass
class ConditionalInjected(Injected):
    condition: Injected[bool]
    true: Injected
    false: Injected

    def dependencies(self) -> Set[str]:
        return self.condition.dependencies() | {"session"}

    def get_provider(self):
        def task(condition, session: "IObjectGraph"):
            if condition:
                return session[self.true]
            else:
                return session[self.false]

        return Injected.bind(task, condition=self.condition).get_provider()

    def dynamic_dependencies(self) -> Set[str]:
        return self.condition.dynamic_dependencies() | \
            self.true.dynamic_dependencies() | \
            self.false.dynamic_dependencies() | {"session"}

    def __repr_expr__(self):
        return f"({self.true.__repr_expr__()} if {self.condition.__repr_expr__()} else {self.false.__repr_expr__()})"


@dataclass
class InjectedCache(Injected[T]):
    """
    A specialized Injected class that handles the caching of program execution results.

    The InjectedCache class is designed to manage caching within a dependency injection framework. It ensures that if a program's execution result, based on certain dependencies, is already known (cached), it does not need to be recalculated. This mechanism is particularly useful for operations that are computationally expensive or require resources that are costly to access repeatedly.

    Attributes:
    -----------
    cache : Injected[Dict]
        An Injected dictionary that represents the cache storage.

    program : Injected[T]
        The program whose result needs to be cached. This is typically a complex operation or query.

    program_dependencies : List[Injected]
        A list of dependencies required by the program. These dependencies are monitored for changes that might invalidate the cache.

    Methods:
    --------
    __post_init__(self):
        Ensures the 'program' attribute is of type 'Injected' and sets up the internal caching mechanism.

    get_provider(self):
        Retrieves the provider for the Injected instance, which is the caching mechanism itself in this case.

    dependencies(self) -> Set[str]:
        Returns the set of dependencies' names required by the caching mechanism.

    dynamic_dependencies(self) -> Set[str]:
        Computes and returns a set of dynamic dependencies by combining the cache's own dependencies and the program's dynamic dependencies.

    __hash__(self):
        Returns the hash of the 'impl' attribute, which represents the unique configuration of the cache.

    Usage:
    ------
    The InjectedCache is not typically created directly by users. Instead, it's often part of a larger dependency injection framework where caching is required. When a certain condition or set of conditions is met, the InjectedCache object checks its internal storage (the 'cache' attribute) to determine whether the current operation's result already exists. If it does, the cached result is returned, saving time and resources. Otherwise, the operation is performed, and the result is stored in the cache for future use.

    This class significantly optimizes performance, especially in scenarios where operations are repeated with the same parameters or contexts, and computational resources are scarce or expensive.
    """
    cache: Injected[Dict]
    program: Injected[T]
    program_dependencies: List[Injected]

    def __post_init__(self):
        self.program = Injected.ensure_injected(self.program)

        async def impl(t):
            from loguru import logger
            resolver, cache, *deps = t
            logger.info(f"Checking for cache with deps:{deps}")
            sha256_key = hashlib.sha256(str(deps).encode()).hexdigest()
            hash_key = sha256_key
            if hash_key not in cache:
                logger.info(f"Cache miss for {deps}")
                data = await resolver[self.program]
                cache[hash_key] = data
            else:
                logger.info(f"Cache hit for {deps},loading ...")
            res = cache[hash_key]
            logger.info(f"Cache hit for {deps}, loaded")
            return res

        self.impl = Injected.list(
            Injected.by_name("__resolver__"),
            self.cache,
            *self.program_dependencies
        ).map(impl)
        assert isinstance(self.impl, Injected)
        assert isinstance(self.program, Injected)

    def get_provider(self):
        return self.impl.get_provider()

    def dependencies(self) -> Set[str]:
        return self.impl.dependencies()

    def dynamic_dependencies(self) -> Set[str]:
        return self.impl.dynamic_dependencies() | \
            self.program.dynamic_dependencies()

    def __hash__(self):
        return hash(self.impl)

    def __repr_expr__(self):
        return f"InjectedCache({self.cache.__repr_expr__()}, {self.program.__repr_expr__()}, {self.program_dependencies})"


class IAsyncDict(abc.ABC):
    @abc.abstractmethod
    async def get(self, key):
        pass

    @abc.abstractmethod
    async def set(self, key, value):
        pass

    @abc.abstractmethod
    async def delete(self, key):
        pass

    @abc.abstractmethod
    async def contains(self, key):
        pass


async def auto_await(tgt):
    if inspect.isawaitable(tgt):
        return await tgt
    else:
        return tgt


@dataclass
class AsyncInjectedCache(Injected[T]):
    cache: Injected[IAsyncDict]
    program: Injected[Awaitable[T]]
    program_dependencies: list[Injected]

    def __post_init__(self):
        self.program = Injected.ensure_injected(self.program)
        assert isinstance(self.program, Injected)
        assert isinstance(self.program_dependencies, list), f"program_dependencies:{self.program_dependencies}"

        from pinjected.v2.resolver import AsyncResolver
        # @cached_coroutine
        async def impl(__resolver__: AsyncResolver, cache: IAsyncDict, deps: list):
            # deps are all awaited here.
            # deps are only used to calc hash key
            from loguru import logger
            assert isinstance(cache, IAsyncDict)
            logger.info(f"Checking cache for {self.program} with deps:{deps}")
            sha256_key = hashlib.sha256(str(deps).encode()).hexdigest()
            hash_key = sha256_key
            if not await cache.contains(hash_key):
                logger.info(f"Cache miss for {deps} in {cache}")
                data = await __resolver__[self.program]
                logger.info(f"Cache miss for {deps}, tried {cache}, writing...")
                await cache.set(hash_key, data)
                logger.info(f"Writen to cache for {deps} to {cache}")
            else:
                logger.info(f"Cache hit for {deps},loading from {cache}")
            try:
                res = await cache.get(hash_key)
                logger.info(f"Cache hit for {deps}, loaded from {cache}")
            except Exception as e:
                logger.warning(f"failed to get from cache:{e}, recalculating")
                res = await __resolver__[self.program]
                await cache.set(hash_key, res)
                logger.info(f"recalculated and written to cache for {deps} to {cache}")
            return res

        self.impl = Injected.bind(
            impl,
            __resolver__=Injected.by_name("__resolver__"),
            cache=self.cache,
            deps=Injected.list(*self.program_dependencies)
        )

        assert isinstance(self.impl, Injected)
        assert isinstance(self.program, Injected)

    def get_provider(self):
        return self.impl.get_provider()

    def dependencies(self) -> Set[str]:
        return self.impl.dependencies()

    def dynamic_dependencies(self) -> Set[str]:
        return self.impl.dynamic_dependencies() | \
            self.program.dynamic_dependencies()

    def __hash__(self):
        return hash(self.impl)

    def __repr_expr__(self):
        return f"AsyncInjectedCache({self.cache.__repr_expr__()}, {self.program.__repr_expr__()}, {self.program_dependencies})"


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

    def __repr_expr__(self):
        return f"GeneratedInjected({self.impl}, {self.dependencies()})"


class InjectedWithDynamicDependencies(Injected[T]):
    __match_args__ = ("src", "_dynamic_dependencies")

    def __init__(self, src: Injected, dynamic_dependencies: Set[str]):
        super(InjectedWithDynamicDependencies, self).__init__()
        self.src = src
        assert isinstance(dynamic_dependencies,
                          set), f"dynamic_dependencies should be set, but got {dynamic_dependencies}"
        self._dynamic_dependencies = dynamic_dependencies

    def dependencies(self) -> Set[str]:
        return self.src.dependencies()

    def get_provider(self):
        return self.src.get_provider()

    def dynamic_dependencies(self) -> Set[str]:
        return self.src.dynamic_dependencies() | self._dynamic_dependencies

    def __repr_expr__(self):
        return self.src.__repr_expr__()


class MappedInjected(Injected):
    __match_args__ = ("src", "f")

    def __init__(self, src: Injected[T], f: Callable[[T], Awaitable[U]], original_mapper):
        super(MappedInjected, self).__init__()
        assert inspect.iscoroutinefunction(f), f"{f} is not a coroutine function"
        self.src = src
        self.f: Callable[[T], Awaitable[U]] = f
        self.original_mapper = original_mapper

    def dependencies(self) -> Set[str]:
        return self.src.dependencies()

    def get_provider(self):
        async def impl(**kwargs):
            assert self.dependencies() == set(
                kwargs.keys())  # this is fine but get_provider returns wrong signatured func
            if not inspect.iscoroutinefunction(self.src.get_provider()):
                raise RuntimeError(f"provider is not a corountine function:{self.src}")
            tmp = await self.src.get_provider()(**kwargs)
            # logger.info(f"original result:{tmp}")
            # logger.info(f"mapper function:{self.f}")
            data = await self.f(tmp)
            # logger.info(f"mapped result:{data}")
            return data

        return create_function(self.get_signature(), func_impl=impl)

    def dynamic_dependencies(self) -> Set[str]:
        return self.src.dynamic_dependencies()

    def __repr_expr__(self):
        return f"{self.src.__repr_expr__()}.map({self.original_mapper})"


def extract_dependency_including_self(f: Union[type, Callable]):
    if isinstance(f, type):  # it's a constructor and we must use __init__ for backward compatibility.
        argspec = inspect.getfullargspec(f.__init__)
        return set(argspec.args)
    elif isinstance(f, Callable):
        argspec = inspect.getfullargspec(f)
        return set(argspec.args)
    else:
        raise RuntimeError(f"input:{f} is not either type or Callable")


def extract_dependency(dep: Union[str, type, Callable, Injected, DelegatedVar[Injected]]) -> Set[str]:
    if isinstance(dep, str):
        return {dep}
    elif isinstance(dep, type):  # it's a constructor and we must use __init__ for backward compatibility.
        argspec = inspect.getfullargspec(dep.__init__)
        return set(argspec.args) - {'self'}
    elif isinstance(dep, DelegatedVar):
        return extract_dependency(dep.eval())
    elif isinstance(dep, Injected):
        return dep.dependencies()
    elif isinstance(dep, Callable):
        try:
            argspec = inspect.getfullargspec(dep)
        except Exception as e:
            from loguru import logger
            logger.error(f"failed to get argspec of {dep}. of type {type(dep)}")
            raise e

        return set(argspec.args) - {'self'}
    else:
        raise RuntimeError(f"dep must be either str/type/Callable/Injected. got {type(dep)}")


async def solve_injection(dep: Union[str, type, Callable, Injected], kwargs: dict):
    if isinstance(dep, str):
        return kwargs[dep]
    elif isinstance(dep, DelegatedVar):
        return await solve_injection(dep.eval(), kwargs)
    elif isinstance(dep, Injected):
        return await solve_injection(dep.get_provider(), kwargs)
    elif isinstance(dep, (type, Callable)) and inspect.iscoroutinefunction(dep):
        return await dep(**{k: kwargs[k] for k in extract_dependency(dep)})
    elif isinstance(dep, (type, Callable)):
        return dep(**{k: kwargs[k] for k in extract_dependency(dep)})
    else:
        raise RuntimeError(f"dep must be one of str/type/Callable/Injected. got {type(dep)}")


def combine_image_store(a, b):
    # do anything
    return a + b


def assert_kwargs_type(v):
    if isinstance(v, DelegatedVar):
        return
    if v == abc.ABCMeta:
        raise TypeError(f"Unexpected: {v}")
    if isinstance(v, str):
        return
    if isinstance(v, type):
        return
    if isinstance(v, Callable):
        return
    if isinstance(v, Injected):
        return

    else:
        raise TypeError(f"{type(v)} is not any of [str,type,Callable,Injected],but {v}")


class InjectedFunction(Injected[T]):
    # since the behavior differs in classes extending Generic[T]
    __match_args__ = ("target_function", "kwargs_mapping")

    def __init__(self,
                 original_function,
                 target_function: Callable,
                 kwargs_mapping: Dict[str, Union[str, type, Callable, Injected, DelegatedVar]],
                 dynamic_dependencies: Optional[Set[str]] = None
                 ):
        # I think we need to know where this class is instantiated outside of pinjected_package
        from loguru import logger
        self.origin_frame = get_instance_origin("pinjected")
        self.original_function = original_function
        super().__init__()
        assert not isinstance(target_function, (Injected, DelegatedVar))
        assert callable(target_function)
        self.target_function = target_function
        assert inspect.iscoroutinefunction(self.target_function), f"{self.target_function} is not a coroutine function"
        self.kwargs_mapping: dict[str, Injected] = copy(kwargs_mapping)
        for k, v in self.kwargs_mapping.items():
            if isinstance(v, DelegatedVar):
                v = v.eval()
                self.kwargs_mapping[k] = v
            assert_kwargs_type(v)
            if v == abc.ABCMeta:
                raise TypeError(f"Unexpected kwargs set.{k}:{v}")
        # logger.info(f"InjectedFunction:{self.target_function} kwargs_mapping:{self.kwargs_mapping}")
        org_deps = extract_dependency(self.target_function)
        logger.trace(f"tgt:{target_function} original dependency:{org_deps}")
        missings = {d for d in org_deps if d not in self.kwargs_mapping}
        logger.trace(f"now missing {missings}")
        # logger.warning(f"created InjectedFunction:{inspect.signature(target_function)}")
        # assert "self" not in inspect.signature(target_function).parameters
        self.missings = missings
        if dynamic_dependencies is None:
            dynamic_dependencies = set()
        self._dynamic_dependencies = dynamic_dependencies

    def override_mapping(self, **kwargs: Union[str, type, Callable, Injected]):
        return InjectedFunction(self.target_function, {**self.kwargs_mapping, **kwargs})

    def get_provider(self):
        signature = self.get_signature()

        async def impl(**kwargs):
            from loguru import logger
            deps = dict()

            async def update(key):
                if key not in deps:
                    if key in self.kwargs_mapping:
                        mapped = self.kwargs_mapping[key]
                    else:
                        mapped = key
                    try:
                        deps[key] = await solve_injection(mapped, kwargs)
                    except Exception as e:
                        logger.error(f"failed to solve injection for {key}:{mapped} from {kwargs}")
                        raise e

            tasks = []
            logger.trace(f"missings:{self.missings},kwargs_mapping:{self.kwargs_mapping}")
            for mdep in self.missings:
                tasks.append(update(mdep))
            for k, dep in self.kwargs_mapping.items():
                tasks.append(update(k))
            await asyncio.gather(*tasks)
            # logger.info(f"calling function:{self.target_function.__name__}{inspect.signature(self.target_function)}")
            # logger.info(f"src mapping:{self.kwargs_mapping}")
            # logger.info(f"with deps:{deps}")
            logger.trace(f"awaiting target function:{self.target_function}")
            logger.trace(f"deps:{deps}")
            res = await self.target_function(**deps)
            # assert not inspect.iscoroutinefunction(res),f"result of awaiting {self.target_function} is a coroutine function:{res}"
            return res

        # you have to add a prefix 'provider'""
        return create_function(func_signature=signature, func_impl=impl)

    def dependencies(self) -> Set[str]:
        # ahhhh this recursively demands for injection.
        # we need to distinguish what and what not to recursively inject
        res = set()
        for mdep in self.missings:
            d = extract_dependency(mdep)
            assert isinstance(d, set), f"extracted dependency is not a set:{d}, from {mdep}"
            res |= d
            # logger.info(f"deps of missing:{d}")
        for k, dep in self.kwargs_mapping.items():
            d = extract_dependency(dep)
            assert isinstance(d, set), f"extracted dependency is not a set:{d}, from {mdep}"
            res |= d
            # logger.info(f"deps of dependency({k}):{d}")
        return res

    # def __str__(self):
    #    return f"""InjectedFunction(target={self.target_function},kwargs_mapping={self.kwargs_mapping})"""
    def dynamic_dependencies(self) -> Set[str]:
        return self._dynamic_dependencies

    def __repr_expr__(self):
        # func_name = self.original_function.__name__
        # orig_file = Path(self.original_function.__original_file__)
        # orig_line = self.original_function.__original_code__
        # return f"<f {func_name}@{orig_file.name}>"
        kwargs_repr = []
        for k, v in self.kwargs_mapping.items():
            match v:
                case str(v):
                    kwargs_repr.append(f"{k}=${v}")
                case type(v):
                    kwargs_repr.append(f"{k}=${v.__name__}")
                case Injected():
                    kwargs_repr.append(f"{k}={v.__repr_expr__()}")
                case c if callable(v):
                    kwargs_repr.append(f"{k}={v.__name__}")
                case unknown:
                    kwargs_repr.append(f"{k}={unknown}")
        kwargs_repr = ", ".join(kwargs_repr)
        return f"{self.original_function.__name__}<{kwargs_repr}>"


class InjectedPure(Injected[T]):
    __match_args__ = ("value",)

    def __init__(self, value):
        super().__init__()
        self.value = value

    def dependencies(self) -> Set[str]:
        return set()

    def get_provider(self):
        async def impl():
            return self.value

        return create_function(func_signature=self.get_signature(), func_impl=impl)

    def __str__(self):
        return f"Pure({self.value})"

    def __repr__(self):
        return str(self)

    def dynamic_dependencies(self) -> Set[str]:
        return set()

    def __repr_expr__(self):
        return f"<{self.value}>"


class InjectedByName(Injected[T]):
    __match_args__ = ("name",)

    def __init__(self, name):
        super().__init__()
        self.name = name

    def dependencies(self) -> Set[str]:
        return {self.name}

    def get_provider(self):
        async def impl(**kwargs):
            return kwargs[self.name]

        return create_function(func_signature=self.get_signature(), func_impl=impl)

    def __str__(self):
        return f"InjectedByName({self.name})"

    def __repr__(self):
        return str(self)

    def dynamic_dependencies(self) -> Set[str]:
        return set()

    def __repr_expr__(self):
        return f"${self.name}"


class ZippedInjected(Injected[Tuple[A, B]]):
    __match_args__ = ("a", "b")

    def __init__(self, a: Injected[A], b: Injected[B]):
        super().__init__()
        raise RuntimeError("deprecated")
        assert isinstance(a, Injected), f"got {type(a)} for a"
        assert isinstance(b, Injected), f"got {type(b)} for b"
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

    def dynamic_dependencies(self) -> Set[str]:
        return self.a.dynamic_dependencies() | self.b.dynamic_dependencies()

    def __repr_expr__(self):
        return f"({self.a.__repr_expr__()}, {self.b.__repr_expr__()})"


class MZippedInjected(Injected):
    __match_args__ = ("srcs",)

    def __init__(self, *srcs: Injected):
        super().__init__()
        self.srcs = [Injected.ensure_injected(item) for item in srcs]
        assert all(isinstance(s, Injected) for s in self.srcs), self.srcs

    def dependencies(self) -> Set[str]:
        res = set()
        for s in self.srcs:
            res |= s.dependencies()

        return res

    def get_provider(self):
        async def impl(**kwargs):  # can we pickle this though?
            res = []
            for s in self.srcs:
                r = s.get_provider()(**{k: kwargs[k] for k in s.dependencies()})
                if not inspect.iscoroutinefunction(s.get_provider()):
                    raise RuntimeError(f"provider is not a corountine function:{s}")
                res.append(r)
            return tuple(await asyncio.gather(*res))

        signature = self.get_signature()
        return create_function(func_signature=signature, func_impl=impl)

    def dynamic_dependencies(self) -> Set[str]:
        res = set()
        for s in self.srcs:
            res |= s.dynamic_dependencies()

        return res

    def __repr_expr__(self):
        return f"({', '.join([s.__repr_expr__() for s in self.srcs])})"


class DictInjected(Injected):
    __match_args__ = ("srcs",)

    def __init__(self, **srcs: Injected):
        super().__init__()
        self.srcs = {k: Injected.ensure_injected(v) for k, v in srcs.items()}
        assert all(isinstance(s, Injected) for s in self.srcs.values()), self.srcs
        from loguru import logger
        logger.warning(f"use of DictInjected is deprecated. use Injected.dict instead.")

    def dependencies(self) -> Set[str]:
        res = set()
        for s in self.srcs.values():
            res |= s.dependencies()

        return res

    def get_provider(self):
        async def impl(**kwargs):  # can we pickle this though?
            res = {}
            tasks = {}
            async with TaskGroup() as tg:
                for k, s in self.srcs.items():
                    r = s.get_provider()(**{k: kwargs[k] for k in s.dependencies()})
                    if not inspect.iscoroutinefunction(s.get_provider()):
                        raise RuntimeError(f"provider is not a corountine function:{s}")
                    tasks[k] = tg.create_task(r)
            for k, t in tasks.items():
                res[k] = await t
            return res

        signature = self.get_signature()
        return create_function(func_signature=signature, func_impl=impl)

    def dynamic_dependencies(self) -> Set[str]:
        res = set()
        for s in self.srcs.values():
            res |= s.dynamic_dependencies()

        return res

    def __repr_expr__(self):
        return f"{{{', '.join([f'{k}:{v.__repr_expr__()}' for k, v in self.srcs.items()])}}})"


def _injected_factory(**targets: Injected):
    def _impl(f):
        return Injected.inject_partially(f, **targets)

    return _impl


class InjectedWithDefaultDesign(Injected):
    __match_args__ = ('src', 'default_design_path')

    def __init__(self, src: Injected, default_design_path: str):
        super().__init__()
        self.src = src  # why does this receive 4 play buttons?
        self.default_design_path: str = default_design_path

    def dependencies(self) -> Set[str]:
        return self.src.dependencies()

    def get_provider(self):
        return self.src.get_provider()


def with_default(design_path: str):
    def _impl(f):
        return InjectedWithDefaultDesign(Injected.ensure_injected(f), design_path)

    return _impl


@dataclass
class RunnableInjected(Injected):
    src: Injected
    design_path: str
    working_dir: str

    def dependencies(self) -> Set[str]:
        return self.src.dependencies()

    def get_provider(self):
        return self.src.get_provider()


@dataclass
class PartialInjectedFunction(Injected):
    src: Injected[Callable]
    args_modifier: Optional[ArgsModifier] = None

    def __post_init__(self):
        assert isinstance(self.src, Injected), f"src:{self.src} is not an Injected"

    def __call__(self, *args, **kwargs) -> DelegatedVar:
        """
        we need 'await' call here.
        So, we need Await AST too.
        """
        # We need to find which one to keep...
        # for that, we need to keep the signature of the original function.
        # Then, replace args/kwargs.
        if self.args_modifier is not None:
            args, kwargs, causes = self.args_modifier(args, kwargs)
            causes: list[Injected]
            called = self.src.proxy(*args, **kwargs)
            dyn_deps = set()
            for c in causes:
                assert isinstance(c, (Injected, DelegatedVar)), f"causes:{causes} is not an Injected, but {type(c)}"
                if isinstance(c, DelegatedVar):
                    c = c.eval()
                dyn = c.dynamic_dependencies()
                assert isinstance(dyn, set), f"dyn:{dyn} is not a set"
                dyn_deps |= c.dynamic_dependencies()
            called = called.eval().add_dynamic_dependencies(dyn_deps)
            return called.proxy
        return self.src.proxy(*args, **kwargs)

    def dependencies(self) -> Set[str]:
        return self.src.dependencies()

    def get_provider(self):
        # logger.warning(f"PartialInjectedFunction.get_provider() is called here.")
        return self.src.get_provider()

    def __hash__(self):
        return hash(self.src)

    def dynamic_dependencies(self) -> Set[str]:
        return self.src.dynamic_dependencies()

    def __repr_expr__(self):
        return f"{self.src.__repr_expr__()}"


def add_viz_metadata(metadata: Dict[str, Any]):
    def impl(tgt: Injected):
        if not hasattr(tgt, '__viz_metadata__'):
            tgt.__viz_metadata__ = dict()
        tgt.__viz_metadata__.update(metadata)
        return tgt

    return impl

def _en_tuple(*items):
    return tuple(items)

def _en_list(*items):
    return list(items)

