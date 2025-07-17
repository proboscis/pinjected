"""
Tests for pytest fixture integration v2 with shared resolver support.
"""

import random
import sys
from typing import Protocol

import pytest

from pinjected import design, injected, Injected
from pinjected.pytest_fixtures_v2 import (
    DesignFixturesV2,
    register_fixtures_from_design_v2,
)


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
    print(f"[DEBUG] Generated random value: {value}")  # Debug output
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

# Register fixtures at module level
fixtures = DesignFixturesV2(shared_resolver_test_design, __file__)
fixtures.caller_module = sys.modules[__name__]
fixtures.register_all(
    async_=True, sync=False
)  # Only async fixtures to avoid event loop issues


class TestSharedResolverV2:
    """Test that resolver is shared across fixtures in a single test."""

    @pytest.mark.asyncio
    async def test_async_fixtures_share_resolver(
        self, shared_random_async, service_a_async, service_b_async
    ):
        """Test that async fixtures share the same resolver and random value."""
        print("\n[TEST] Starting async shared resolver test")

        # Get values from fixtures
        shared = await shared_random_async
        a = await service_a_async
        b = await service_b_async

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

        print("[TEST] ✓ All fixtures share the same resolver!")

    @pytest.mark.asyncio
    async def test_different_tests_get_different_resolvers_part1(
        self, shared_random_async
    ):
        """First test to capture a random value."""
        shared = await shared_random_async
        TestSharedResolverV2._test1_value = shared["value"]
        TestSharedResolverV2._test1_id = shared["id"]
        print(f"\n[TEST1] Captured random value: {shared['value']}")

    @pytest.mark.asyncio
    async def test_different_tests_get_different_resolvers_part2(
        self, shared_random_async
    ):
        """Second test should get a different random value."""
        shared = await shared_random_async
        print(f"\n[TEST2] Got random value: {shared['value']}")

        if hasattr(TestSharedResolverV2, "_test1_value"):
            print(
                f"[TEST2] Previous test had value: {TestSharedResolverV2._test1_value}"
            )
            # Different tests should have different values (new resolver per test)
            # This might occasionally fail due to random collision, but unlikely with range 1000-9999
            assert (
                shared["value"] != TestSharedResolverV2._test1_value
                or shared["id"] != TestSharedResolverV2._test1_id
            ), "Different tests should get different resolvers"
            print("[TEST2] ✓ Different tests have different resolvers!")


# Test the convenience function
def test_convenience_function_v2():
    """Test the register_fixtures_from_design_v2 convenience function."""
    # Create a simple test design
    test_design = design(
        test_value=Injected.pure("hello"),
        test_number=Injected.pure(42),
    )

    # This would normally be in conftest.py
    fixtures = register_fixtures_from_design_v2(
        test_design, prefix="conv_", exclude={"test_number"}
    )

    # Check that only test_value was registered (with prefix)
    assert "conv_test_value" in fixtures._registered_fixtures
    assert "conv_test_number" not in fixtures._registered_fixtures

    print("\n[TEST] ✓ Convenience function works correctly!")
