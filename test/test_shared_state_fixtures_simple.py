"""Simplified test for shared state in pytest fixtures without conftest interference."""

import pytest
import random
import os
import sys
import warnings
from typing import Protocol, Dict

# Add parent directory to path to import pinjected
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pinjected import injected, design
from pinjected.pytest_fixtures import register_fixtures_from_design

pytestmark = pytest.mark.skip(reason="pytest_fixtures.py is deprecated")

warnings.filterwarnings(
    "ignore", category=DeprecationWarning, message=".*register_fixtures_from_design.*"
)


class SharedCounterProtocol(Protocol):
    def __call__(self) -> Dict[str, int]: ...


class ServiceAProtocol(Protocol):
    def __call__(self, shared_counter: Dict[str, int]) -> Dict[str, any]: ...


class ServiceBProtocol(Protocol):
    def __call__(self, shared_counter: Dict[str, int]) -> Dict[str, any]: ...


# Shared counter test
@injected(protocol=SharedCounterProtocol)
def shared_counter():
    """A shared counter that should be the same across fixtures in same scope."""
    value = random.randint(1000, 9999)
    print(f"Creating shared_counter with value: {value}")
    return {"count": value}


@injected(protocol=ServiceAProtocol)
def service_a(shared_counter):
    """Service A that depends on shared counter."""
    print(f"Service A accessing counter: {shared_counter['count']}")
    return {"service": "A", "counter_value": shared_counter["count"]}


@injected(protocol=ServiceBProtocol)
def service_b(shared_counter):
    """Service B that depends on shared counter."""
    print(f"Service B accessing counter: {shared_counter['count']}")
    return {"service": "B", "counter_value": shared_counter["count"]}


# Register fixtures
test_design = design(
    shared_counter=shared_counter,
    service_a=service_a,
    service_b=service_b,
)

register_fixtures_from_design(test_design)


@pytest.mark.asyncio
async def test_shared_state_works(service_a, service_b, shared_counter):
    """Test that all fixtures share the same counter instance."""
    print(f"\nTest - shared_counter: {shared_counter['count']}")
    print(f"Test - service_a counter: {service_a['counter_value']}")
    print(f"Test - service_b counter: {service_b['counter_value']}")

    # All three should have the same counter value
    assert service_a["counter_value"] == service_b["counter_value"]
    assert service_a["counter_value"] == shared_counter["count"]
    assert service_b["counter_value"] == shared_counter["count"]

    # Verify service names
    assert service_a["service"] == "A"
    assert service_b["service"] == "B"

    print("✅ Shared state test passed!")
