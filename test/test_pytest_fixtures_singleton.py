"""
Tests for pytest fixtures with singleton pattern to ensure shared state.
"""

import random
import sys
from typing import Protocol

import pytest

from pinjected import design, injected
from pinjected.pytest_fixtures_simple import DesignFixtures


# Singleton storage
_shared_state = {}


# Protocol definitions
class RandomProviderProtocol(Protocol):
    def __call__(self) -> dict: ...


class ServiceAProtocol(Protocol):
    def __call__(self) -> dict: ...


class ServiceBProtocol(Protocol):
    def __call__(self) -> dict: ...


# Singleton random provider
@injected(protocol=RandomProviderProtocol)
def shared_random_provider():
    """Provides shared random value using singleton pattern."""
    if "random_value" not in _shared_state:
        value = random.randint(1000, 9999)
        print(f"\n[DEBUG] Generated random value: {value}")
        _shared_state["random_value"] = {"value": value, "id": id(object())}
    else:
        print(
            f"[DEBUG] Reusing cached random value: {_shared_state['random_value']['value']}"
        )
    return _shared_state["random_value"]


@injected(protocol=ServiceAProtocol)
def service_a_singleton(shared_random=shared_random_provider):
    """Service A that uses shared random provider."""
    random_data = shared_random()
    print(f"[DEBUG] Service A received random value: {random_data['value']}")
    return {
        "name": "service_a",
        "random_value": random_data["value"],
        "random_id": random_data["id"],
    }


@injected(protocol=ServiceBProtocol)
def service_b_singleton(shared_random=shared_random_provider):
    """Service B that uses shared random provider."""
    random_data = shared_random()
    print(f"[DEBUG] Service B received random value: {random_data['value']}")
    return {
        "name": "service_b",
        "random_value": random_data["value"],
        "random_id": random_data["id"],
    }


# Design with singleton shared state
singleton_test_design = design(
    shared_random=shared_random_provider,
    service_a=service_a_singleton,
    service_b=service_b_singleton,
)

# Register fixtures at module level
fixtures = DesignFixtures(singleton_test_design, __file__)
fixtures.caller_module = sys.modules[__name__]
fixtures.register_all()


def setup_function(function):
    """Clear shared state before each test."""
    global _shared_state
    _shared_state.clear()
    print(f"\n[SETUP] Cleared shared state for {function.__name__}")


class TestSingletonResolver:
    """Test that singleton pattern ensures shared state."""

    @pytest.mark.asyncio
    async def test_singleton_fixtures_share_same_value(
        self, shared_random, service_a, service_b
    ):
        """Test that all fixtures share the same singleton random value."""
        print("\n[TEST] Starting singleton resolver test")

        # Get the actual values from fixtures
        shared = shared_random
        a = service_a
        b = service_b

        print(f"[TEST] Shared random value: {shared['value']}")
        print(f"[TEST] Service A random value: {a['random_value']}")
        print(f"[TEST] Service B random value: {b['random_value']}")

        # All should have the same random value
        assert shared["value"] == a["random_value"], (
            "Service A should have same random value"
        )
        assert shared["value"] == b["random_value"], (
            "Service B should have same random value"
        )

        # All should have the same instance ID
        assert shared["id"] == a["random_id"], "Service A should have same random ID"
        assert shared["id"] == b["random_id"], "Service B should have same random ID"

        print("[TEST] ✓ Singleton pattern ensures shared state!")

    @pytest.mark.asyncio
    async def test_different_tests_get_different_values_part1(self, shared_random):
        """First test to capture a random value."""
        value = shared_random["value"]
        TestSingletonResolver._test1_value = value
        print(f"\n[TEST1] Captured random value: {value}")

    @pytest.mark.asyncio
    async def test_different_tests_get_different_values_part2(self, shared_random):
        """Second test should get a different random value due to setup_function."""
        value = shared_random["value"]
        print(f"\n[TEST2] Got random value: {value}")

        if hasattr(TestSingletonResolver, "_test1_value"):
            print(
                f"[TEST2] Previous test had value: {TestSingletonResolver._test1_value}"
            )
            # Different tests should have different values (due to clearing)
            assert value != TestSingletonResolver._test1_value, (
                "Different tests should get different values"
            )
            print("[TEST2] ✓ Different tests have different state!")
