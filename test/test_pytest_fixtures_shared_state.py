"""Test that shared state works correctly in pytest fixtures after our fix."""

import pytest
import random
import warnings
from typing import Protocol, Dict
from pinjected import instance, design, injected
from pinjected.test import register_fixtures_from_design

pytestmark = pytest.mark.skip(reason="pytest_fixtures.py is deprecated")

warnings.filterwarnings(
    "ignore", category=DeprecationWarning, message=".*register_fixtures_from_design.*"
)


class RandomValueProtocol(Protocol):
    def __call__(self) -> int: ...


class ServiceAProtocol(Protocol):
    def __call__(self) -> Dict[str, any]: ...


class ServiceBProtocol(Protocol):
    def __call__(self) -> Dict[str, any]: ...


class AggregateServiceProtocol(Protocol):
    def __call__(self) -> Dict[str, any]: ...


# Create injected functions at module level
@instance
def random_value():
    """A random value that should be shared within the same test."""
    value = random.randint(1000, 9999)
    return value


@instance
def service_a(random_value):
    """Service A that uses the random value."""
    return {"name": "A", "value": random_value}


@instance
def service_b(random_value):
    """Service B that uses the random value."""
    return {"name": "B", "value": random_value}


@instance
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
register_fixtures_from_design(shared_state_design)

# NOTE: Without prefix support, we cannot register the same design with different scopes
# The tests below that expect different scopes will need to be adjusted
# register_fixtures_from_design(shared_state_design, scope="module")


class TestSharedStateInFixtures:
    """Test that our pytest fixtures properly share state within the same scope."""

    @pytest.mark.asyncio
    async def test_function_scope_shares_state(
        self, random_value, service_a, service_b, aggregate_service
    ):
        """Test that function-scoped fixtures share the same dependency instances."""
        # All should have the same random value
        # The fixtures should already contain the resolved values
        actual_random_value = random_value
        actual_service_a = service_a
        actual_service_b = service_b
        actual_aggregate_service = aggregate_service

        assert actual_service_a["value"] == actual_random_value
        assert actual_service_b["value"] == actual_random_value
        assert actual_aggregate_service["direct_value"] == actual_random_value
        assert actual_aggregate_service["service_a_value"] == actual_random_value
        assert actual_aggregate_service["service_b_value"] == actual_random_value

        # Store for comparison with next test
        TestSharedStateInFixtures._func_value_1 = actual_random_value

    @pytest.mark.asyncio
    async def test_function_scope_isolated_between_tests(self, random_value):
        """Test that function-scoped fixtures get new instances in different tests."""
        # Should be different from previous test
        actual_random_value = random_value
        if hasattr(TestSharedStateInFixtures, "_func_value_1"):
            assert actual_random_value != TestSharedStateInFixtures._func_value_1

    @pytest.mark.skip(reason="Module scope test requires prefix support")
    @pytest.mark.asyncio
    async def test_module_scope_shares_state(self, random_value, service_a, service_b):
        """Test that module-scoped fixtures share the same dependency instances."""
        # All should have the same random value
        assert service_a["value"] == random_value
        assert service_b["value"] == random_value

        # Store for comparison across tests
        TestSharedStateInFixtures._mod_value = random_value

    @pytest.mark.skip(reason="Module scope test requires prefix support")
    @pytest.mark.asyncio
    async def test_module_scope_persists_across_tests(self, random_value, service_a):
        """Test that module-scoped fixtures persist across tests in the same module."""
        # Should be the same as in previous test
        assert random_value == TestSharedStateInFixtures._mod_value
        assert service_a["value"] == TestSharedStateInFixtures._mod_value

    @pytest.mark.skip(reason="Different scope test requires prefix support")
    @pytest.mark.asyncio
    async def test_different_scopes_different_instances(self, random_value, service_a):
        """Test that different scopes have different resolver instances."""
        # Function and module scoped values should be different
        # Note: This test may need to be adjusted since we're not using separate registrations
        # for different scopes with the same fixtures
        pass  # Test logic needs to be reconsidered


@pytest.mark.skip(reason="Multiple registration test requires prefix support")
@pytest.mark.asyncio
async def test_edge_case_multiple_registrations():
    """Test that multiple registrations with different prefixes work correctly."""
    # Create a new design
    edge_design = design(
        test_value=lambda: random.randint(100, 200),
        consumer=injected(lambda test_value: {"consumed": test_value}),
    )

    # Register with different prefixes
    register_fixtures_from_design(edge_design)
    # Note: Without prefix support, we can't register the same design twice

    # The registrations should work without errors
    assert True
