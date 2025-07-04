"""Type stubs for pinjected.di.decorators module."""

from typing import TypeVar, overload, Callable, Any, Union
from pinjected.di.injected import Injected, PartialInjectedFunction
from pinjected.di.proxiable import DelegatedVar
from pinjected.di.iproxy import IProxy

_T = TypeVar("_T")
_P = TypeVar("_P")

# Overloads for @injected decorator

# When called with a string - returns DelegatedVar
@overload
def injected(tgt: str) -> DelegatedVar: ...

# When called with a callable/type and protocol - returns IProxy of the protocol type
@overload
def injected(tgt: type[_T], *, protocol: type[_P]) -> IProxy[_P]: ...
@overload
def injected(tgt: Callable[..., _T], *, protocol: type[_P]) -> IProxy[_P]: ...

# When called with a callable/type without protocol - returns DelegatedVar
@overload
def injected(tgt: type[_T], *, protocol: None = None) -> DelegatedVar: ...
@overload
def injected(tgt: Callable[..., _T], *, protocol: None = None) -> DelegatedVar: ...

# When used as a decorator with protocol parameter - returns a decorator that produces IProxy[Protocol]
@overload
def injected(*, protocol: type[_P]) -> Callable[[Callable[..., Any]], IProxy[_P]]: ...

# When used as a decorator without any parameters - returns a decorator that produces DelegatedVar
@overload
def injected() -> Callable[[Callable[..., Any]], DelegatedVar]: ...

# Deprecated functions
def injected_function(
    f: Callable[..., _T], parent_frame: Any = None
) -> PartialInjectedFunction: ...
def injected_instance(f: Callable[..., _T]) -> Injected[_T]: ...
def injected_class(cls: type[_T]) -> DelegatedVar: ...
def injected_method(f: Callable[..., _T]) -> Callable[..., _T]: ...

# Aliases
instance = injected_instance

# Other decorators and utilities
def dynamic(
    *providables: Any,
) -> Callable[
    [Union[Injected[_T], DelegatedVar]], Union[Injected[_T], DelegatedVar]
]: ...
def register(name: str) -> Callable[[Injected[_T]], Injected[_T]]: ...

# Helper functions
def cached_coroutine(coro_func: Callable[..., _T]) -> Callable[..., _T]: ...

# Context manager
from contextlib import _GeneratorContextManager

def reload(*targets: str) -> _GeneratorContextManager[None]: ...

# Internal helper (should not be exposed in public API, but included for completeness)
def _injected_with_protocol(
    tgt: Union[type[_T], Callable[..., _T]],
    protocol: Union[type[_P], None] = None,
    parent_frame: Any = None,
) -> Union[DelegatedVar, IProxy[_P]]: ...
