#!/usr/bin/env python3
"""Proper test for the pinjected call CLI command"""

from typing import Protocol
from pinjected import injected, IProxy, Injected


class SimpleFunctionProtocol(Protocol):
    def __call__(self) -> str: ...


class AddNumbersProtocol(Protocol):
    def __call__(self, x: int, y: int) -> int: ...


class GreetProtocol(Protocol):
    def __call__(self, name: str) -> str: ...


# Create simple @injected functions
@injected(protocol=SimpleFunctionProtocol)
def simple_function() -> str:
    """A simple function with no dependencies"""
    print("Simple function called!")
    return "Success"


@injected(protocol=AddNumbersProtocol)
def add_numbers(x: int, y: int) -> int:
    """Add two numbers"""
    return x + y


@injected(protocol=GreetProtocol)
def greet(name: str) -> str:
    """Create a greeting"""
    return f"Hello, {name}!"


# Create IProxy objects using Injected values
simple_proxy = IProxy(Injected.pure("test"))

# IProxy with injected values - bind to lambda functions
numbers_proxy = IProxy(
    Injected.bind(lambda x, y: x + y, x=Injected.pure(10), y=Injected.pure(20))
)

# IProxy with string value
name_proxy = IProxy(
    Injected.bind(lambda name: f"Hello, {name}!", name=Injected.pure("World"))
)
