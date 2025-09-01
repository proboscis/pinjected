"""Test that verifies shared state works correctly in pytest fixtures."""

import pytest
import random
import warnings
from typing import Protocol, Dict, Any
from pinjected import injected, design
from pinjected.test import register_fixtures_from_design

pytestmark = pytest.mark.skip(reason="pytest_fixtures.py is deprecated")

warnings.filterwarnings(
    "ignore", category=DeprecationWarning, message=".*register_fixtures_from_design.*"
)


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
register_fixtures_from_design(shared_state_design)
register_fixtures_from_design(complex_design)

# Register fixtures with module scope
register_fixtures_from_design(shared_state_design, scope="module")
register_fixtures_from_design(complex_design, scope="module")


class TestSharedStateInPytestFixtures:
    """Test that shared dependencies are properly shared within scope."""

    @pytest.mark.asyncio
    async def test_function_scope_shared_counter(self, service_a, service_b):
        """Test that services share the same counter value in function scope."""
        # Both services should have the same counter value
        # Call the injected functions
        actual_service_a = service_a()
        actual_service_b = service_b()

        assert actual_service_a["counter_value"] == actual_service_b["counter_value"]
        assert actual_service_a["service"] == "A"
        assert actual_service_b["service"] == "B"

    @pytest.mark.asyncio
    async def test_function_scope_complex_dependencies(
        self,
        user_repository,
        order_repository,
        user_service,
    ):
        """Test complex dependency sharing in function scope."""
        # All should share the same database connection
        # Call the injected functions
        actual_user_repository = user_repository()
        actual_order_repository = order_repository()
        actual_user_service = user_service()

        assert (
            actual_user_repository["connection_id"]
            == actual_order_repository["connection_id"]
        )
        assert actual_user_service["db_id"] == actual_user_repository["connection_id"]
        assert (
            actual_user_service["repo_db_id"] == actual_user_repository["connection_id"]
        )

        # Verify they point to the same database object
        assert actual_user_repository["db"] is actual_order_repository["db"]

    @pytest.mark.skip(reason="Module scope test requires prefix support")
    @pytest.mark.asyncio
    async def test_module_scope_shared_counter(self, service_a, service_b):
        """Test that services share the same counter value in module scope."""
        # Both services should have the same counter value
        # Call the injected functions
        actual_service_a = service_a()
        actual_service_b = service_b()

        assert actual_service_a["counter_value"] == actual_service_b["counter_value"]
        assert actual_service_a["service"] == "A"
        assert actual_service_b["service"] == "B"

    @pytest.mark.skip(reason="Module scope test requires prefix support")
    @pytest.mark.asyncio
    async def test_module_scope_persistence_1(self, shared_counter):
        """First test to capture module-scoped counter value."""
        # Store the value in a class variable for comparison
        # Call the injected function
        actual_counter = shared_counter()
        TestSharedStateInPytestFixtures._module_counter_value = actual_counter["count"]
        assert isinstance(actual_counter["count"], int)

    @pytest.mark.skip(reason="Module scope test requires prefix support")
    @pytest.mark.asyncio
    async def test_module_scope_persistence_2(self, shared_counter):
        """Second test to verify module-scoped counter persists."""
        # Should be the same value as in the first test
        # Call the injected function
        actual_counter = shared_counter()
        assert (
            actual_counter["count"]
            == TestSharedStateInPytestFixtures._module_counter_value
        )

    @pytest.mark.skip(reason="Different scope test requires prefix support")
    @pytest.mark.asyncio
    async def test_different_scopes_different_instances(self, shared_counter):
        """Test that different scopes get different instances."""
        # Function and module scoped fixtures should have different values
        # This test cannot work without prefix support
        pass


class TestIsolationBetweenTests:
    """Test that function-scoped fixtures are isolated between tests."""

    @pytest.mark.asyncio
    async def test_isolation_1(self, shared_counter):
        """First test captures function-scoped value."""
        # Call the injected function
        actual_counter = shared_counter()
        TestIsolationBetweenTests._first_value = actual_counter["count"]
        assert isinstance(actual_counter["count"], int)

    @pytest.mark.asyncio
    async def test_isolation_2(self, shared_counter):
        """Second test should get a different value (function scope)."""
        # Should be different from the first test due to function scope
        # Call the injected function
        actual_counter = shared_counter()
        assert actual_counter["count"] != TestIsolationBetweenTests._first_value


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

    # Note: Without prefix support, we cannot register fixtures with the same
    # names from different designs
    register_fixtures_from_design(design1)

    # This test would need to be run with the fixtures, but we're just ensuring
    # the registration doesn't fail
    assert True  # Registration succeeded without errors
