"""Simple test to verify shared state works correctly in pytest fixtures."""

import pytest
import random
import warnings
from typing import Protocol, Dict
from pinjected import injected, design
from pinjected.test import register_fixtures_from_design

warnings.filterwarnings(
    "ignore", category=DeprecationWarning, message=".*register_fixtures_from_design.*"
)


class SimpleCounterProtocol(Protocol):
    def __call__(self) -> int: ...


class ServiceUsingCounterProtocol(Protocol):
    def __call__(self, simple_counter: int) -> Dict[str, int]: ...


# Simple counter that increments each time it's created
@injected(protocol=SimpleCounterProtocol)
def simple_counter():
    """A simple counter that should be shared within same scope."""
    value = random.randint(1000, 9999)
    print(f"\n[CREATED] simple_counter: {value}")
    return value


@injected(protocol=ServiceUsingCounterProtocol)
def service_using_counter(simple_counter):
    """Service that uses the counter."""
    print(f"[SERVICE] using counter: {simple_counter}")
    return {"counter": simple_counter}


# Create design and register fixtures
test_design = design(
    simple_counter=simple_counter,
    service_using_counter=service_using_counter,
)

register_fixtures_from_design(test_design)


@pytest.mark.asyncio
async def test_shared_state_works(simple_counter, service_using_counter):
    """Test that all fixtures share the same counter instance."""
    print(f"\nTest - simple_counter: {simple_counter}")
    print(f"Test - service_using_counter: {service_using_counter}")

    # Both should have the same counter value
    assert service_using_counter["counter"] == simple_counter

    print("✅ Shared state test passed!")


@pytest.mark.asyncio
async def test_isolation_between_tests_1(simple_counter):
    """First test to capture counter value."""
    test_isolation_between_tests_1._value = simple_counter
    assert isinstance(simple_counter, int)


@pytest.mark.asyncio
async def test_isolation_between_tests_2(simple_counter):
    """Second test should get a different value (function scope)."""
    # Should be different from the first test due to function scope
    assert simple_counter != test_isolation_between_tests_1._value
