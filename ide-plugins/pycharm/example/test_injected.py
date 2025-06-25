"""Test file for debugging IDE plugin configuration extraction."""

from pinjected import injected, instance, IProxy
from pinjected.di.decorators import injected_function


# Simple injected function
@injected
def simple_injected(logger):
    """A simple injected function that uses logger."""
    logger.info("Hello from simple_injected")
    return "simple result"


# Instance function (no dependencies)
@instance
def simple_instance():
    """An instance function with no dependencies."""
    print("Hello from simple_instance")
    return "instance result"


# IProxy variable
simple_iproxy = IProxy(lambda: "iproxy result")


# Another injected function with multiple dependencies
@injected
def complex_injected(logger, simple_injected, /):
    """An injected function with multiple dependencies."""
    logger.info(f"Got result from simple: {simple_injected}")
    return f"complex: {simple_injected}"


# Test with injected_function decorator
@injected_function
def decorated_func():
    """Function with injected_function decorator."""
    return "decorated"


# Regular function (should NOT show gutter icon)
def regular_function():
    """A regular Python function."""
    return "regular"


# Regular variable (should NOT show gutter icon)
regular_var = "not injected"


# Add __design__ to specify default design path
__design__ = None  # Will use the default pinjected internal design
