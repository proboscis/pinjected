"""Test fixture for validating parameter rules for @injected functions."""

from pinjected import injected
from typing import Protocol


class User:
    """User model."""

    pass


class Product:
    """Product model."""

    pass


# VALID: Exactly one parameter without default
class ValidFunc1Protocol(Protocol):
    def __call__(self) -> str: ...


@injected(protocol=ValidFunc1Protocol)
def valid_single_param(x: User, param=42, param2=128):
    """Valid: x is the only parameter without default."""
    return f"Processing {x}"


class ValidFunc2Protocol(Protocol):
    def __call__(self) -> int: ...


@injected(protocol=ValidFunc2Protocol)
def valid_with_many_defaults(product: Product, limit=10, offset=0, sort="asc"):
    """Valid: product is the only parameter without default."""
    return 1


class ValidFunc3Protocol(Protocol):
    def __call__(self) -> bool: ...


@injected(protocol=ValidFunc3Protocol)
def valid_minimal(user: User):
    """Valid: user is the only parameter (no defaults needed if it's the only one)."""
    return True


# INVALID: Multiple parameters without defaults
class InvalidFunc1Protocol(Protocol):
    def __call__(self) -> str: ...


@injected(protocol=InvalidFunc1Protocol)
def invalid_two_params(x: User, y: Product, param=42):
    """Invalid: x and y both lack defaults."""
    return "Invalid"


class InvalidFunc2Protocol(Protocol):
    def __call__(self) -> None: ...


@injected(protocol=InvalidFunc2Protocol)
def invalid_three_params(a: User, b: Product, c: str):
    """Invalid: three parameters without defaults."""
    pass


# INVALID: No parameters
class InvalidFunc3Protocol(Protocol):
    def __call__(self) -> None: ...


@injected(protocol=InvalidFunc3Protocol)
def invalid_no_params():
    """Invalid: no parameters at all."""
    pass


# INVALID: All parameters have defaults
class InvalidFunc4Protocol(Protocol):
    def __call__(self) -> None: ...


@injected(protocol=InvalidFunc4Protocol)
def invalid_all_defaults(x: User = None, y: Product = None):
    """Invalid: all parameters have defaults (no target param)."""
    pass


# Edge case: Mixed types
class EdgeCase1Protocol(Protocol):
    def __call__(self) -> str: ...


@injected(protocol=EdgeCase1Protocol)
def edge_complex_type(data: dict[str, User], timeout=30.0):
    """Valid: data is the only param without default."""
    return "OK"


# Test async functions
class AsyncValidProtocol(Protocol):
    async def __call__(self) -> str: ...


@injected(protocol=AsyncValidProtocol)
async def a_valid_async(user: User, timeout=30):
    """Valid async: user is the only parameter without default."""
    return "async result"


class AsyncInvalidProtocol(Protocol):
    async def __call__(self) -> None: ...


@injected(protocol=AsyncInvalidProtocol)
async def a_invalid_async(x: User, y: Product):
    """Invalid async: two parameters without defaults."""
    pass
