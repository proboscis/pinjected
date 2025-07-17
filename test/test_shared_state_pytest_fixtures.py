"""Test that verifies shared state works correctly in pytest fixtures."""

import pytest
import random
from typing import Protocol, Dict, Any
from pinjected import injected, design
from pinjected.test import register_fixtures_from_design


class SharedCounterProtocol(Protocol):
    def __call__(self) -> Dict[str, int]: ...


class ServiceAProtocol(Protocol):
    def __call__(self, shared_counter: Dict[str, int]) -> Dict[str, Any]: ...


class ServiceBProtocol(Protocol):
    def __call__(self, shared_counter: Dict[str, int]) -> Dict[str, Any]: ...


class DatabaseConnectionProtocol(Protocol):
    def __call__(self) -> Dict[str, Any]: ...


class UserRepositoryProtocol(Protocol):
    def __call__(self, database_connection: Dict[str, Any]) -> Dict[str, Any]: ...


class OrderRepositoryProtocol(Protocol):
    def __call__(self, database_connection: Dict[str, Any]) -> Dict[str, Any]: ...


class UserServiceProtocol(Protocol):
    def __call__(
        self, user_repository: Dict[str, Any], database_connection: Dict[str, Any]
    ) -> Dict[str, Any]: ...


# Test 1: Simple shared state test
@injected(protocol=SharedCounterProtocol)
def shared_counter():
    """A shared counter that should be the same across fixtures in same scope."""
    return {"count": random.randint(1000, 9999)}


@injected(protocol=ServiceAProtocol)
def service_a(shared_counter):
    """Service A that depends on shared counter."""
    return {"service": "A", "counter_value": shared_counter["count"]}


@injected(protocol=ServiceBProtocol)
def service_b(shared_counter):
    """Service B that depends on shared counter."""
    return {"service": "B", "counter_value": shared_counter["count"]}


# Test 2: Complex shared dependencies
@injected(protocol=DatabaseConnectionProtocol)
def database_connection():
    """Shared database connection."""
    connection_id = random.randint(10000, 99999)
    return {"connection_id": connection_id, "tables": {}}


@injected(protocol=UserRepositoryProtocol)
def user_repository(database_connection):
    """User repository using shared database."""
    return {
        "db": database_connection,
        "table": "users",
        "connection_id": database_connection["connection_id"],
    }


@injected(protocol=OrderRepositoryProtocol)
def order_repository(database_connection):
    """Order repository using shared database."""
    return {
        "db": database_connection,
        "table": "orders",
        "connection_id": database_connection["connection_id"],
    }


@injected(protocol=UserServiceProtocol)
def user_service(user_repository, database_connection):
    """User service with multiple dependencies."""
    return {
        "repo": user_repository,
        "db_id": database_connection["connection_id"],
        "repo_db_id": user_repository["connection_id"],
    }


# Create test designs
shared_state_design = design(
    shared_counter=shared_counter,
    service_a=service_a,
    service_b=service_b,
)

complex_design = design(
    database_connection=database_connection,
    user_repository=user_repository,
    order_repository=order_repository,
    user_service=user_service,
)


# Register fixtures with function scope (default)
register_fixtures_from_design(shared_state_design, prefix="func_")
register_fixtures_from_design(complex_design, prefix="func_complex_")

# Register fixtures with module scope
register_fixtures_from_design(shared_state_design, scope="module", prefix="module_")
register_fixtures_from_design(complex_design, scope="module", prefix="module_complex_")


class TestSharedStateInPytestFixtures:
    """Test that shared dependencies are properly shared within scope."""

    @pytest.mark.asyncio
    async def test_function_scope_shared_counter(self, func_service_a, func_service_b):
        """Test that services share the same counter value in function scope."""
        # Both services should have the same counter value
        assert func_service_a["counter_value"] == func_service_b["counter_value"]
        assert func_service_a["service"] == "A"
        assert func_service_b["service"] == "B"

    @pytest.mark.asyncio
    async def test_function_scope_complex_dependencies(
        self,
        func_complex_user_repository,
        func_complex_order_repository,
        func_complex_user_service,
    ):
        """Test complex dependency sharing in function scope."""
        # All should share the same database connection
        assert (
            func_complex_user_repository["connection_id"]
            == func_complex_order_repository["connection_id"]
        )
        assert (
            func_complex_user_service["db_id"]
            == func_complex_user_repository["connection_id"]
        )
        assert (
            func_complex_user_service["repo_db_id"]
            == func_complex_user_repository["connection_id"]
        )

        # Verify they point to the same database object
        assert func_complex_user_repository["db"] is func_complex_order_repository["db"]

    @pytest.mark.asyncio
    async def test_module_scope_shared_counter(
        self, module_service_a, module_service_b
    ):
        """Test that services share the same counter value in module scope."""
        # Both services should have the same counter value
        assert module_service_a["counter_value"] == module_service_b["counter_value"]
        assert module_service_a["service"] == "A"
        assert module_service_b["service"] == "B"

    @pytest.mark.asyncio
    async def test_module_scope_persistence_1(self, module_shared_counter):
        """First test to capture module-scoped counter value."""
        # Store the value in a class variable for comparison
        TestSharedStateInPytestFixtures._module_counter_value = module_shared_counter[
            "count"
        ]
        assert isinstance(module_shared_counter["count"], int)

    @pytest.mark.asyncio
    async def test_module_scope_persistence_2(self, module_shared_counter):
        """Second test to verify module-scoped counter persists."""
        # Should be the same value as in the first test
        assert (
            module_shared_counter["count"]
            == TestSharedStateInPytestFixtures._module_counter_value
        )

    @pytest.mark.asyncio
    async def test_different_scopes_different_instances(
        self, func_shared_counter, module_shared_counter
    ):
        """Test that different scopes get different instances."""
        # Function and module scoped fixtures should have different values
        assert func_shared_counter["count"] != module_shared_counter["count"]


class TestIsolationBetweenTests:
    """Test that function-scoped fixtures are isolated between tests."""

    @pytest.mark.asyncio
    async def test_isolation_1(self, func_shared_counter):
        """First test captures function-scoped value."""
        TestIsolationBetweenTests._first_value = func_shared_counter["count"]
        assert isinstance(func_shared_counter["count"], int)

    @pytest.mark.asyncio
    async def test_isolation_2(self, func_shared_counter):
        """Second test should get a different value (function scope)."""
        # Should be different from the first test due to function scope
        assert func_shared_counter["count"] != TestIsolationBetweenTests._first_value


@pytest.mark.asyncio
async def test_edge_case_multiple_designs():
    """Test registering multiple designs doesn't interfere with shared state."""
    # Create two separate designs with overlapping dependency names
    design1 = design(
        shared_data=lambda: {"design": 1, "value": random.randint(1, 100)},
        consumer_a=injected(
            lambda shared_data: {"from": "design1", "data": shared_data["value"]}
        ),
    )

    design2 = design(
        shared_data=lambda: {"design": 2, "value": random.randint(1000, 2000)},
        consumer_b=injected(
            lambda shared_data: {"from": "design2", "data": shared_data["value"]}
        ),
    )

    # Register both with different prefixes
    register_fixtures_from_design(design1, prefix="d1_")
    register_fixtures_from_design(design2, prefix="d2_")

    # This test would need to be run with the fixtures, but we're just ensuring
    # the registration doesn't fail
    assert True  # Registration succeeded without errors
