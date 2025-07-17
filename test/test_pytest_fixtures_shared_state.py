"""Test that shared state works correctly in pytest fixtures after our fix."""

import pytest
import random
from typing import Protocol, Dict
from pinjected import injected, design
from pinjected.test import register_fixtures_from_design


class RandomValueProtocol(Protocol):
    def __call__(self) -> int: ...


class ServiceAProtocol(Protocol):
    def __call__(self, random_value: int) -> Dict[str, any]: ...


class ServiceBProtocol(Protocol):
    def __call__(self, random_value: int) -> Dict[str, any]: ...


class AggregateServiceProtocol(Protocol):
    def __call__(
        self, random_value: int, service_a: Dict[str, any], service_b: Dict[str, any]
    ) -> Dict[str, any]: ...


# Create injected functions at module level
@injected(protocol=RandomValueProtocol)
def random_value():
    """A random value that should be shared within the same test."""
    value = random.randint(1000, 9999)
    return value


@injected(protocol=ServiceAProtocol)
def service_a(random_value):
    """Service A that uses the random value."""
    return {"name": "A", "value": random_value}


@injected(protocol=ServiceBProtocol)
def service_b(random_value):
    """Service B that uses the random value."""
    return {"name": "B", "value": random_value}


@injected(protocol=AggregateServiceProtocol)
def aggregate_service(random_value, service_a, service_b):
    """Service that aggregates all values."""
    return {
        "direct_value": random_value,
        "service_a_value": service_a["value"],
        "service_b_value": service_b["value"],
    }


# Create design and register fixtures
shared_state_design = design(
    random_value=random_value,
    service_a=service_a,
    service_b=service_b,
    aggregate_service=aggregate_service,
)

# Register with function scope (default)
register_fixtures_from_design(shared_state_design, prefix="func_")

# Register with module scope
register_fixtures_from_design(shared_state_design, scope="module", prefix="mod_")


class TestSharedStateInFixtures:
    """Test that our pytest fixtures properly share state within the same scope."""

    @pytest.mark.asyncio
    async def test_function_scope_shares_state(
        self, func_random_value, func_service_a, func_service_b, func_aggregate_service
    ):
        """Test that function-scoped fixtures share the same dependency instances."""
        # All should have the same random value
        assert func_service_a["value"] == func_random_value
        assert func_service_b["value"] == func_random_value
        assert func_aggregate_service["direct_value"] == func_random_value
        assert func_aggregate_service["service_a_value"] == func_random_value
        assert func_aggregate_service["service_b_value"] == func_random_value

        # Store for comparison with next test
        TestSharedStateInFixtures._func_value_1 = func_random_value

    @pytest.mark.asyncio
    async def test_function_scope_isolated_between_tests(self, func_random_value):
        """Test that function-scoped fixtures get new instances in different tests."""
        # Should be different from previous test
        if hasattr(TestSharedStateInFixtures, "_func_value_1"):
            assert func_random_value != TestSharedStateInFixtures._func_value_1

    @pytest.mark.asyncio
    async def test_module_scope_shares_state(
        self, mod_random_value, mod_service_a, mod_service_b
    ):
        """Test that module-scoped fixtures share the same dependency instances."""
        # All should have the same random value
        assert mod_service_a["value"] == mod_random_value
        assert mod_service_b["value"] == mod_random_value

        # Store for comparison across tests
        TestSharedStateInFixtures._mod_value = mod_random_value

    @pytest.mark.asyncio
    async def test_module_scope_persists_across_tests(
        self, mod_random_value, mod_service_a
    ):
        """Test that module-scoped fixtures persist across tests in the same module."""
        # Should be the same as in previous test
        assert mod_random_value == TestSharedStateInFixtures._mod_value
        assert mod_service_a["value"] == TestSharedStateInFixtures._mod_value

    @pytest.mark.asyncio
    async def test_different_scopes_different_instances(
        self, func_random_value, mod_random_value
    ):
        """Test that different scopes have different resolver instances."""
        # Function and module scoped values should be different
        assert func_random_value != mod_random_value


@pytest.mark.asyncio
async def test_edge_case_multiple_registrations():
    """Test that multiple registrations with different prefixes work correctly."""
    # Create a new design
    edge_design = design(
        test_value=lambda: random.randint(100, 200),
        consumer=injected(lambda test_value: {"consumed": test_value}),
    )

    # Register with different prefixes
    register_fixtures_from_design(edge_design, prefix="edge1_")
    register_fixtures_from_design(edge_design, prefix="edge2_")

    # The registrations should work without errors
    assert True
