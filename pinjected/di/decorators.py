import asyncio
import functools
import inspect
from collections.abc import Callable
from contextlib import contextmanager
from typing import Union, Optional, overload, Any

from returns.maybe import Some

from pinjected.di.implicit_globals import IMPLICIT_BINDINGS
from pinjected.di.injected import Injected, PartialInjectedFunction, extract_dependency
from pinjected.di.proxiable import DelegatedVar
from pinjected.di.util import get_code_location
from pinjected.v2.binds import BindInjected
from pinjected.v2.keys import StrBindKey


def _extract_injection_targets(sig: inspect.Signature) -> dict:
    """Extract injection targets from function signature.

    :param sig: Function signature to analyze
    :return: Dictionary mapping parameter names to injection targets
    """
    tgts = dict()
    for k, v in sig.parameters.items():
        if k.startswith("__"):
            tgts[k] = Injected.by_name(k)
        elif k.startswith("_"):
            tgts[k] = Injected.by_name(k[1:])
        elif v.kind == inspect.Parameter.POSITIONAL_ONLY:
            tgts[k] = Injected.by_name(k)
    return tgts


def injected_function(f, parent_frame=None) -> PartialInjectedFunction:
    """
    .. deprecated:: Use ``@injected`` instead with positional-only parameters (parameters before ``/``) for dependencies.

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
    import warnings

    warnings.warn(
        "injected_function is deprecated. Use @injected with positional-only parameters (parameters before '/') for dependencies.",
        DeprecationWarning,
        stacklevel=2,
    )

    # Extract injection targets from signature
    sig: inspect.Signature = inspect.signature(f)
    tgts = _extract_injection_targets(sig)

    # Set parent frame if not provided
    if parent_frame is None:
        parent_frame = inspect.currentframe().f_back

    # Create injected function
    new_f = Injected.inject_partially(f, **tgts)

    # Determine key name based on type
    key_name = f"new_{f.__name__}" if isinstance(f, type) else f.__name__

    # Register in implicit bindings
    from pinjected.di.metadata.bind_metadata import BindMetadata

    IMPLICIT_BINDINGS[StrBindKey(key_name)] = BindInjected(
        new_f,
        _metadata=Some(
            BindMetadata(code_location=Some(get_code_location(parent_frame)))
        ),
    )

    return new_f


def injected_instance(
    f=None, *, callable: bool = False
) -> Union[Injected, Callable[[Callable], Injected]]:
    """
    The ``injected_instance`` (also accessible as ``instance``) is a decorator that creates an
    ``Injected`` instance from a function. This function essentially converts a regular function
    that returns an instance into an ``Injected`` type that can be used for dependency injection,
    particularly within the context of a design setup.

    :param f: The function that generates an instance, typically utilizing dependencies.
    :type f: Function
    :param callable: If True, indicates that the function returns a callable object (e.g., a function,
                     closure, or callable class instance) that should be called directly. This allows
                     the linter to understand that calls to the returned value are intentional.
    :type callable: bool

    :return: An instance of ``Injected`` that wraps the provided function, or a decorator if f is None.
    :rtype: Union[Injected, Callable[[Callable], Injected]]

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
        design = design(
            logger=logger
        )

        # Usage of the designed provider
        _logger = design.provide('logger')  # returns a Logger instance
        _logger.info('hello world')

    :Example with callable=True:

    .. code-block:: python

        @instance(callable=True)
        def event_handler_factory(logger):
            def handle_event(event):
                logger.info(f"Handling event: {event}")
                # Process event...
            return handle_event

        # Now, 'event_handler_factory' returns a callable that can be invoked directly
        design = design(
            event_handler_factory=event_handler_factory
        )

        # Usage
        handler = design.provide('event_handler_factory')  # returns the handle_event function
        handler(some_event)  # This direct call is allowed and won't trigger PINJ004

    This approach allows the function to be integrated into a dependency injection system easily,
    with the ``Injected`` instance handling the complexities of resolving and managing dependencies.
    """

    def decorator(func):
        # is_coroutine = inspect.iscoroutinefunction(func)
        # if is_coroutine:
        #     func = cached_coroutine(func)

        sig: inspect.Signature = inspect.signature(func)
        tgts = {k: Injected.by_name(k) for k, v in sig.parameters.items()}
        called_partial = Injected.inject_partially(func, **tgts)()

        # logger.info(f"called_partial:{called_partial}->dir:{called_partial.value.func}")
        instance = called_partial.eval()
        # instance = Injected.bind(func)
        from pinjected.di.metadata.bind_metadata import BindMetadata

        # instance.__is_async_function__ = is_coroutine
        IMPLICIT_BINDINGS[StrBindKey(func.__name__)] = BindInjected(
            instance,
            _metadata=Some(
                BindMetadata(
                    code_location=Some(
                        get_code_location(inspect.currentframe().f_back)
                    ),
                    is_callable_instance=callable,
                )
            ),
        )
        return instance.proxy

    # Handle the case where @instance is used with or without parentheses
    if f is None:
        # Called as @instance(callable=True)
        return decorator
    else:
        # Called as @instance
        return decorator(f)


@overload
def injected(tgt: str) -> DelegatedVar: ...


@overload
def injected(
    tgt: type | Callable, *, protocol: Optional[Any] = None
) -> DelegatedVar: ...


@overload
def injected(
    *, protocol: Optional[Any] = None
) -> Callable[[Callable], DelegatedVar]: ...


def injected(
    tgt: Optional[Union[str, type, Callable]] = None, *, protocol: Optional[Any] = None
) -> Union[DelegatedVar, Callable[[Callable], DelegatedVar]]:
    """
    The ``injected`` decorator automates dependency injection, transforming a target (string, class, or callable)
    into an ``Injected`` instance. It specifically treats positional-only parameters as dependencies,
    automatically injecting them. In contrast, non-positional-only parameters are left as-is for later
    specification during function or method invocation.

    :param tgt: The target indicating what is to be injected. This can be:
                1. ``str``: the name of a dependency.
                2. ``type``: a class that needs automated dependency injection for instantiation.
                3. ``Callable``: a function or method requiring dependencies.
    :param protocol: Optional Protocol class that defines the interface for the injected function.
                     Enables better type safety and IDE support.
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

        # With protocol specification
        class FetchUserProtocol(Protocol):
            def __call__(self, user_id: str) -> User: ...

        @injected(protocol=FetchUserProtocol)
        def fetch_user(db, /, user_id: str) -> User:
            return db.get_user(user_id)

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
    if tgt is None:
        # Called as @injected(protocol=SomeProtocol) or @injected()
        def decorator(func: Callable) -> DelegatedVar:
            return _injected_with_protocol(
                func,
                protocol=protocol,
                parent_frame=inspect.currentframe().f_back.f_back,
            )

        return decorator

    if isinstance(tgt, str):
        # String targets don't support protocol
        if protocol is not None:
            raise TypeError(
                "Protocol parameter is not supported for string dependencies"
            )
        return Injected.by_name(tgt).proxy

    if isinstance(tgt, type) or callable(tgt):
        return _injected_with_protocol(
            tgt, protocol=protocol, parent_frame=inspect.currentframe().f_back
        )

    raise TypeError(f"Invalid target type: {type(tgt)}")


def _injected_with_protocol(
    tgt: Union[type, Callable], protocol: Optional[Any] = None, parent_frame=None
) -> DelegatedVar:
    """Internal helper to handle protocol-aware injection."""
    # First check what injected_function returns
    sig: inspect.Signature = inspect.signature(tgt)
    tgts = dict()
    if parent_frame is None:
        parent_frame = inspect.currentframe().f_back

    # Extract dependencies based on naming conventions and position-only parameters
    for k, v in sig.parameters.items():
        if k.startswith("__"):
            tgts[k] = Injected.by_name(k)
        elif k.startswith("_"):
            tgts[k] = Injected.by_name(k[1:])
        elif v.kind == inspect.Parameter.POSITIONAL_ONLY:
            tgts[k] = Injected.by_name(k)

    new_f = Injected.inject_partially(tgt, **tgts)

    # Determine the key name
    if isinstance(tgt, type):
        key_name = f"new_{tgt.__name__}"
    else:
        key_name = tgt.__name__

    # Create metadata with protocol information
    from pinjected.di.metadata.bind_metadata import BindMetadata

    metadata = BindMetadata(
        code_location=Some(get_code_location(parent_frame)), protocol=protocol
    )

    # Store in IMPLICIT_BINDINGS with protocol metadata
    IMPLICIT_BINDINGS[StrBindKey(key_name)] = BindInjected(
        new_f,
        _metadata=Some(metadata),
    )

    # Add protocol attribute to the result for runtime access
    if protocol is not None:
        new_f.__protocol__ = protocol

    return new_f


def injected_class(cls):
    return injected_function(cls)


def injected_method(f):
    _impl = injected_function(f)

    def impl(self, *args, **kwargs):
        return _impl(self, *args, **kwargs)

    return impl


class CachedAwaitable:
    def __init__(self, coro):
        # logger.warning(f'CachedAwaitable created with {coro}')
        self.coro = coro
        self._cache = None
        self._has_run = False
        self._lock = asyncio.Lock()

    def __await__(self):
        return self._get_result().__await__()

    async def _get_result(self):
        from pinjected.pinjected_logging import logger

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
        all_deps = set()
        for p in providables:
            all_deps.update(extract_dependency(p))
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


def register(name):
    def impl(tgt: Injected):
        from pinjected.di.metadata.bind_metadata import BindMetadata

        IMPLICIT_BINDINGS[StrBindKey(name)] = BindInjected(
            Injected.ensure_injected(tgt),
            _metadata=Some(
                BindMetadata(
                    code_location=Some(get_code_location(inspect.currentframe().f_back))
                )
            ),
        )
        return tgt

    return impl
