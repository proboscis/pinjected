import inspect
from contextlib import contextmanager
from typing import Union, Callable, Annotated

from returns.maybe import Some

from pinjected import Injected
from pinjected.di.implicit_globals import IMPLICIT_BINDINGS
from pinjected.di.injected import PartialInjectedFunction, extract_dependency
from pinjected.di.proxiable import DelegatedVar
from pinjected.di.util import get_code_location
import functools
import asyncio

from pinjected.v2.binds import BindInjected
from pinjected.v2.keys import StrBindKey


def injected_function(f, parent_frame=None) -> PartialInjectedFunction:
    """
    Wraps a function, injecting dependencies for parameters that start with an underscore or are positional-only.
    This enhanced version supports class methods, recognizing and bypassing the 'self' parameter automatically.
    The function also registers the newly created function in the ``IMPLICIT_BINDINGS`` global dictionary.

    :param f: The target function where dependencies will be injected. This can be a standard function or a class method.
    :param parent_frame: The parent frame to inspect for getting the code location. If not provided, the system automatically determines the appropriate frame.
    :return: A new function with dependencies injected, suitable for both standalone functions and class methods.

    **Example Usage:**

    Given a class with a method that requires dependency injection:

    .. code-block:: python
        @injected_function
        class MyClass:
            dependency1: object
            def my_method(self, arg2):
                # Method implementation here
                # use self.dependency1

        # now we have Injected[Callable[[],MyClass]]
        g[MyClass]() # returns an instance of MyClass with dependency1 injected

    .. note::
        The function or a class will be automatically registered with its name, in the global ``IMPLICIT_BINDINGS`` dictionary, making it recognizable by the system's dependency injection mechanisms.
    """
    # How can we make this work on a class method?
    sig: inspect.Signature = inspect.signature(f)
    tgts = dict()
    if parent_frame is None:
        parent_frame = inspect.currentframe().f_back
    for k, v in sig.parameters.items():
        if k.startswith("__"):
            tgts[k] = Injected.by_name(k)
        elif k.startswith("_"):
            tgts[k] = Injected.by_name(k[1:])
        elif v.kind == inspect.Parameter.POSITIONAL_ONLY:
            tgts[k] = Injected.by_name(k)


    new_f = Injected.inject_partially(f, **tgts)
    if isinstance(f, type):
        key_name = f"new_{f.__name__}"
    else:
        key_name = f.__name__

    from pinjected.di.metadata.bind_metadata import BindMetadata
    IMPLICIT_BINDINGS[StrBindKey(key_name)] = BindInjected(
        new_f,
        _metadata=Some(BindMetadata(code_location=Some(get_code_location(parent_frame)))),
    )

    return new_f


def injected_instance(f) -> Injected:
    """
    The ``injected_instance`` (also accessible as ``instance``) is a decorator that creates an
    ``Injected`` instance from a function. This function essentially converts a regular function
    that returns an instance into an ``Injected`` type that can be used for dependency injection,
    particularly within the context of a design setup.

    :param f: The function that generates an instance, typically utilizing dependencies.
    :type f: Function

    :return: An instance of ``Injected`` that wraps the provided function.
    :rtype: Injected

    :Example:

    .. code-block:: python

        @instance
        def logger(dep1, dep2):
            from logging import getLogger
            # maybe use dep1, dep2...
            return getLogger(__name__)

        # Now, 'logger' is an instance of 'Injected' specialized with 'Logger'.
        assert type(logger) == Injected  # True for Injected[Logger]

        # This 'Injected' instance can be contributed to a design like so:
        design = providers(
            logger=logger
        )

        # Usage of the designed provider
        _logger = design.provide('logger')  # returns a Logger instance
        _logger.info('hello world')

    This approach allows the function to be integrated into a dependency injection system easily,
    with the ``Injected`` instance handling the complexities of resolving and managing dependencies.
    """

    is_coroutine = inspect.iscoroutinefunction(f)
    # if is_coroutine:
    #     f = cached_coroutine(f)

    sig: inspect.Signature = inspect.signature(f)
    tgts = {k: Injected.by_name(k) for k, v in sig.parameters.items()}
    called_partial = Injected.inject_partially(f, **tgts)()
    from loguru import logger
    #logger.info(f"called_partial:{called_partial}->dir:{called_partial.value.func}")
    instance = called_partial.eval()
    # instance = Injected.bind(f)
    from pinjected.di.metadata.bind_metadata import BindMetadata
    #instance.__is_async_function__ = is_coroutine
    IMPLICIT_BINDINGS[StrBindKey(f.__name__)] = BindInjected(
        instance,
        _metadata=Some(BindMetadata(code_location=Some(get_code_location(inspect.currentframe().f_back))))
    )
    return instance.proxy


def injected(tgt: Union[str, type, Callable]):
    """
    The ``injected`` decorator automates dependency injection, transforming a target (string, class, or callable) 
    into an ``Injected`` instance. It specifically treats positional-only parameters as dependencies, 
    automatically injecting them. In contrast, non-positional-only parameters are left as-is for later 
    specification during function or method invocation.

    :param tgt: The target indicating what is to be injected. This can be:
                1. ``str``: the name of a dependency.
                2. ``type``: a class that needs automated dependency injection for instantiation.
                3. ``Callable``: a function or method requiring dependencies.
    :return: An appropriate ``Injected`` instance, proxy, or wrapped entity with dependencies injected, 
             contingent on the nature of ``tgt``.

    **Usage Example:**

    .. code-block:: python

        @injected
        def function_requiring_dependencies(dependency1: Type1, /, normal_param: Type2):
            # Function body here. 'dependency1' is injected, 'normal_param' must be provided during call.

        @injected
        class ClassRequiringDependencies:
            def __init__(self, dependency1: Type1, /, normal_param: Type2):
                # Constructor body. 'dependency1' is injected, 'normal_param' is left for object creation time.

        # For direct dependency retrieval via a string identifier.
        dependency_instance = injected("dependency_key")

    In these examples, ``dependency1`` is a positional-only parameter and treated as a dependency to be 
    automatically injected. On the other hand, ``normal_param`` is a non-positional-only parameter. It's 
    not considered a dependency within the automatic injection process, and thus, must be specified 
    during the routine call or object instantiation.
    

    .. note::
        This approach enforces clear demarcation between automatically resolved dependencies 
        (positional-only) and those parameters that developers need to provide explicitly during 
        function/method invocation or class instantiation. This strategy enhances code readability 
        and ensures that the dependency injection framework adheres to explicit programming practices.
    """
    if isinstance(tgt, str):
        return Injected.by_name(tgt).proxy
    elif isinstance(tgt, type):
        return injected_function(tgt, parent_frame=inspect.currentframe().f_back)
    elif callable(tgt):
        return injected_function(tgt, parent_frame=inspect.currentframe().f_back)


def injected_class(cls):
    return injected_function(cls)


def injected_method(f):
    _impl = injected_function(f)

    def impl(self, *args, **kwargs):
        return _impl(self, *args, **kwargs)

    return impl


class CachedAwaitable:
    def __init__(self, coro):
        from loguru import logger
        # logger.warning(f'CachedAwaitable created with {coro}')
        self.coro = coro
        self._cache = None
        self._has_run = False
        self._lock = asyncio.Lock()

    def __await__(self):
        return self._get_result().__await__()

    async def _get_result(self):
        from loguru import logger
        # logger.warning(f"accessing cached coroutine:{self.coro}")
        async with self._lock:
            if not self._has_run:
                try:
                    self._cache = await self.coro
                except Exception as e:
                    logger.error(f"cached coroutine failed with {e},{self.coro}")
                    self._cache = e
                    raise e
                finally:
                    self._has_run = True
        if isinstance(self._cache, Exception):
            raise self._cache
        return self._cache


def cached_coroutine(coro_func):
    @functools.wraps(coro_func)
    def wrapper(*args, **kwargs):
        return CachedAwaitable(coro_func(*args, **kwargs))

    functools.update_wrapper(wrapper, coro_func)
    return wrapper


instance = injected_instance


def dynamic(*providables):
    """
    Use this to specify dynamic dependencies for an Injected instance.
    """

    def impl(tgt):
        all_deps = set(sum([list(extract_dependency(p)) for p in providables], start=[]))
        match tgt:
            case Injected() as i:
                return i.add_dynamic_dependencies(*all_deps)
            case DelegatedVar() as d:
                return impl(d.eval()).proxy

    return impl


@contextmanager
def reload(*targets: str):
    """
    A stub marker decorator for pinjected to reload the target function on console run.
    :param targets:
    :return:
    """
    yield
