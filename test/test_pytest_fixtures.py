"""
Tests for pytest fixture integration.
"""

import sys
from typing import Protocol

import pytest

from pinjected import design, injected, Injected
from pinjected.pytest_fixtures import DesignFixtures


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
        result = greeting("World")
        assert result == "Hello, World!"

    @pytest.mark.asyncio
    async def test_counter_fixture(self, counter):
        """Test that counter fixture works."""
        # Each test gets its own counter instance
        assert counter() == 1
        assert counter() == 2
        assert counter() == 3

    @pytest.mark.asyncio
    async def test_multiple_fixtures(self, greeting, counter):
        """Test using multiple fixtures in one test."""
        assert greeting("Test") == "Hello, Test!"
        assert counter() == 1  # New counter instance


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
        fixtures.register_all(prefix="test_", exclude={"service_c"})

        # Check that fixtures were registered correctly
        assert hasattr(mock_module, "test_service_a")
        assert hasattr(mock_module, "test_service_b")
        assert not hasattr(mock_module, "test_service_c")

        # Check registered fixture names
        assert fixtures._registered_fixtures == {"test_service_a", "test_service_b"}
