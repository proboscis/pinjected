"""
Tests for batch pytest fixture integration.
"""

import random
import sys
from typing import Protocol

import pytest

from pinjected import design, injected
from pinjected.pytest_fixtures_batch import BatchDesignFixtures


# Protocol definitions
class RandomGeneratorProtocol(Protocol):
    def __call__(self) -> dict: ...


class ServiceAProtocol(Protocol):
    def __call__(self, shared_random: dict, /) -> dict: ...


class ServiceBProtocol(Protocol):
    def __call__(self, shared_random: dict, /) -> dict: ...


# Injected functions
@injected(protocol=RandomGeneratorProtocol)
def shared_random_generator():
    """Generates a random value - should only be called once per test."""
    value = random.randint(1000, 9999)
    print(f"\n[DEBUG] Generated random value: {value}")  # Debug output
    return {"value": value, "id": id(object())}


@injected(protocol=ServiceAProtocol)
def service_a(shared_random: dict, /):
    """Service A that depends on shared random value."""
    print(f"[DEBUG] Service A received random value: {shared_random['value']}")
    return {
        "name": "service_a",
        "random_value": shared_random["value"],
        "random_id": shared_random["id"],
    }


@injected(protocol=ServiceBProtocol)
def service_b(shared_random: dict, /):
    """Service B that also depends on shared random value."""
    print(f"[DEBUG] Service B received random value: {shared_random['value']}")
    return {
        "name": "service_b",
        "random_value": shared_random["value"],
        "random_id": shared_random["id"],
    }


# Design with shared dependencies
shared_resolver_test_design = design(
    shared_random=shared_random_generator,
    service_a=service_a,
    service_b=service_b,
)

# Register batch fixtures at module level
fixtures = BatchDesignFixtures(shared_resolver_test_design, __file__)
fixtures.caller_module = sys.modules[__name__]
fixtures.register_batch()


class TestBatchResolver:
    """Test that batch resolver properly shares state."""

    @pytest.mark.asyncio
    async def test_batch_fixtures_share_same_resolver(
        self, shared_random, service_a, service_b
    ):
        """Test that all fixtures share the same resolver and random value."""
        print("\n[TEST] Starting batch resolver test")

        # All fixtures should now have the actual resolved values
        print(f"[TEST] Shared random value: {shared_random['value']}")
        print(f"[TEST] Service A random value: {service_a['random_value']}")
        print(f"[TEST] Service B random value: {service_b['random_value']}")

        # All should have the same random value
        assert shared_random["value"] == service_a["random_value"], (
            "Service A should have same random value"
        )
        assert shared_random["value"] == service_b["random_value"], (
            "Service B should have same random value"
        )

        # All should have the same instance ID
        assert shared_random["id"] == service_a["random_id"], (
            "Service A should have same random ID"
        )
        assert shared_random["id"] == service_b["random_id"], (
            "Service B should have same random ID"
        )

        print("[TEST] ✓ All fixtures share the same resolver!")

    @pytest.mark.asyncio
    async def test_batch_context_fixture(self, pinjected_context):
        """Test accessing the batch context directly."""
        print("\n[TEST] Testing batch context fixture")

        # The context should contain all resolved values
        assert "shared_random" in pinjected_context
        assert "service_a" in pinjected_context
        assert "service_b" in pinjected_context

        # Values should be properly resolved
        assert isinstance(pinjected_context["shared_random"], dict)
        assert "value" in pinjected_context["shared_random"]

        print(f"[TEST] Context contains {len(pinjected_context)} resolved bindings")
        print("[TEST] ✓ Batch context works correctly!")
