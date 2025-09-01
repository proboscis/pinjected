"""
Tests for pytest fixture integration.
"""

import sys
from typing import Protocol

import pytest
from pinjected import design, injected, Injected
from pinjected.pytest_fixtures import DesignFixtures

pytestmark = pytest.mark.skip(reason="pytest_fixtures.py is deprecated")


# Protocol definitions
class GreetingProtocol(Protocol):
    def __call__(self, name: str) -> str: ...


class CounterProtocol(Protocol):
    def __call__(self) -> int: ...


# Simple injected functions
@injected(protocol=GreetingProtocol)
def greeting_service():
    """Simple greeting service."""

    def greet(name: str) -> str:
        return f"Hello, {name}!"

    return greet


@injected(protocol=CounterProtocol)
def counter_service():
    """Simple counter service."""
    count = 0

    def increment():
        nonlocal count
        count += 1
        return count

    return increment


# Test design
simple_test_design = design(
    greeting=greeting_service,
    counter=counter_service,
)

# Register fixtures at module level
fixtures = DesignFixtures(simple_test_design, __file__)
fixtures.caller_module = sys.modules[__name__]
fixtures.register_all()


class TestSimpleFixtures:
    """Test basic fixture functionality."""

    @pytest.mark.asyncio
    async def test_greeting_fixture(self, greeting):
        """Test that greeting fixture works."""
        # greeting is a PartiallyInjectedFunction
        # We need to call it first to get the actual greet function
        greet_function = greeting()
        result = greet_function("World")
        assert result == "Hello, World!"

    @pytest.mark.asyncio
    async def test_counter_fixture(self, counter):
        """Test that counter fixture works."""
        # counter is a PartiallyInjectedFunction
        # We need to call it first to get the actual increment function
        increment_function = counter()
        # Each test gets its own counter instance
        assert increment_function() == 1
        assert increment_function() == 2
        assert increment_function() == 3

    @pytest.mark.asyncio
    async def test_multiple_fixtures(self, greeting, counter):
        """Test using multiple fixtures in one test."""
        # Both are PartiallyInjectedFunctions that need to be called
        greet_function = greeting()
        increment_function = counter()

        assert greet_function("Test") == "Hello, Test!"
        assert increment_function() == 1  # New counter instance


class TestConvenienceFunction:
    """Test the convenience function."""

    def test_register_with_options(self):
        """Test registering fixtures with options."""
        # Create a test design
        test_design = design(
            service_a=Injected.pure("A"),
            service_b=Injected.pure("B"),
            service_c=Injected.pure("C"),
        )

        # Create a mock module
        import types

        mock_module = types.ModuleType("test_module")

        # Create fixtures directly and set module before registration
        fixtures = DesignFixtures(test_design)
        fixtures.caller_module = mock_module

        # Now register with options
        fixtures.register_all(exclude={"service_c"})

        # Check that fixtures were registered correctly
        assert hasattr(mock_module, "service_a")
        assert hasattr(mock_module, "service_b")
        assert not hasattr(mock_module, "service_c")

        # Check registered fixture names
        assert fixtures._registered_fixtures == {"service_a", "service_b"}
