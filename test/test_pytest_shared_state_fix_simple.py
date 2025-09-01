"""Simple test to verify shared state works correctly in pytest fixtures."""

import pytest
import random
import warnings
from typing import Protocol, Dict
from pinjected import injected, design
from pinjected.test import register_fixtures_from_design

pytestmark = pytest.mark.skip(reason="pytest_fixtures.py is deprecated")

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
    # Call the injected function to get the actual value
    actual_counter = simple_counter()
    print(f"[SERVICE] using counter: {actual_counter}")
    return {"counter": actual_counter}


# Create design and register fixtures
test_design = design(
    simple_counter=simple_counter,
    service_using_counter=service_using_counter,
)

register_fixtures_from_design(test_design)


@pytest.mark.asyncio
async def test_shared_state_works(simple_counter, service_using_counter):
    """Test that all fixtures share the same counter instance."""
    actual_counter = simple_counter()
    actual_service = service_using_counter()

    print(f"\nTest - simple_counter: {actual_counter}")
    print(f"Test - service_using_counter: {actual_service}")

    assert actual_service["counter"] == actual_counter

    print("✅ Shared state test passed!")


@pytest.mark.asyncio
async def test_isolation_between_tests_1(simple_counter):
    """First test to capture counter value."""
    actual_counter = simple_counter()
    test_isolation_between_tests_1._value = actual_counter
    assert isinstance(actual_counter, int)


@pytest.mark.asyncio
async def test_isolation_between_tests_2(simple_counter):
    """Second test should get a different value (function scope)."""
    actual_counter = simple_counter()
    assert actual_counter != test_isolation_between_tests_1._value
