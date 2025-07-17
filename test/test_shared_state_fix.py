"""Test that verifies shared state works correctly after our fix."""

import pytest
import random
from typing import Protocol, Dict
from pinjected import injected, design
from pinjected.test import register_fixtures_from_design


class TestSharedCounterProtocol(Protocol):
    def __call__(self) -> Dict[str, int]: ...


class TestServiceAProtocol(Protocol):
    def __call__(self, test_shared_counter: Dict[str, int]) -> Dict[str, any]: ...


class TestServiceBProtocol(Protocol):
    def __call__(self, test_shared_counter: Dict[str, int]) -> Dict[str, any]: ...


# Module-level injected functions to avoid PINJ027
@injected(protocol=TestSharedCounterProtocol)
def test_shared_counter():
    """A shared counter that should be the same across fixtures in same scope."""
    value = random.randint(1000, 9999)
    return {"count": value}


@injected(protocol=TestServiceAProtocol)
def test_service_a(test_shared_counter):
    """Service A that depends on shared counter."""
    return {"service": "A", "counter_value": test_shared_counter["count"]}


@injected(protocol=TestServiceBProtocol)
def test_service_b(test_shared_counter):
    """Service B that depends on shared counter."""
    return {"service": "B", "counter_value": test_shared_counter["count"]}


# Create test design
shared_test_design = design(
    test_shared_counter=test_shared_counter,
    test_service_a=test_service_a,
    test_service_b=test_service_b,
)

# Register fixtures with function scope
register_fixtures_from_design(shared_test_design)


class TestSharedStateFix:
    """Test shared state after our pytest fixtures fix."""

    @pytest.mark.asyncio
    async def test_shared_state_in_function_scope(
        self, test_shared_counter, test_service_a, test_service_b
    ):
        """Test that all fixtures share the same counter instance in function scope."""
        # All should have the same counter value
        assert test_service_a["counter_value"] == test_service_b["counter_value"]
        assert test_service_a["counter_value"] == test_shared_counter["count"]
        assert test_service_b["counter_value"] == test_shared_counter["count"]

        # Verify service names
        assert test_service_a["service"] == "A"
        assert test_service_b["service"] == "B"


class ModuleCounterProtocol(Protocol):
    def __call__(self) -> Dict[str, any]: ...


class ModuleServiceProtocol(Protocol):
    def __call__(self, module_counter: Dict[str, any]) -> Dict[str, any]: ...


# Module-scoped injected functions
@injected(protocol=ModuleCounterProtocol)
def module_counter():
    """Module-scoped counter."""
    value = random.randint(10000, 99999)
    return {"count": value, "scope": "module"}


@injected(protocol=ModuleServiceProtocol)
def module_service(module_counter):
    """Service using module-scoped counter."""
    return {"counter": module_counter["count"], "service": "module"}


# Create and register module-scoped design
module_test_design = design(
    module_counter=module_counter,
    module_service=module_service,
)

register_fixtures_from_design(module_test_design, scope="module", prefix="mod_")


class TestModuleScopeSharing:
    """Test that module-scoped fixtures properly share state."""

    _first_counter_value = None

    @pytest.mark.asyncio
    async def test_module_scope_first(self, mod_module_counter, mod_module_service):
        """First test to capture module-scoped values."""
        TestModuleScopeSharing._first_counter_value = mod_module_counter["count"]
        assert mod_module_service["counter"] == mod_module_counter["count"]

    @pytest.mark.asyncio
    async def test_module_scope_second(self, mod_module_counter, mod_module_service):
        """Second test should see same module-scoped values."""
        # Should be the same as in first test
        assert (
            mod_module_counter["count"] == TestModuleScopeSharing._first_counter_value
        )
        assert mod_module_service["counter"] == mod_module_counter["count"]


# Test different scopes get different instances
class TestScopeIsolation:
    """Test that different scopes get different resolver instances."""

    @pytest.mark.asyncio
    async def test_function_vs_module_scope(
        self, test_shared_counter, mod_module_counter
    ):
        """Test that function and module scoped fixtures have different values."""
        # These should be different because they use different resolvers
        assert test_shared_counter["count"] != mod_module_counter["count"]
