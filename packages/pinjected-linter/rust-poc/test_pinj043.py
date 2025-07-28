"""Test cases for PINJ043: No design() in test functions"""

import pytest
import pinjected
from pinjected import design
from pinjected.test import register_fixtures_from_design


# VIOLATION: design() used inside test function
def test_basic_violation():
    with design() as d:
        d.provide("user_service", lambda: "mock_user_service")
        d.provide("database", lambda: {"users": []})

    # This would fail in real test
    pass


# VIOLATION: design() in async test
@pytest.mark.asyncio
async def test_async_violation():
    async with design() as d:
        d.provide("async_service", lambda: "mock_async_service")

    # This would fail in real test
    pass


# VIOLATION: design() with pytest parametrize
@pytest.mark.parametrize("value", [1, 2, 3])
def test_parametrized_violation(value):
    with design() as d:
        d.provide("service", lambda: "mock_service")

    # This would fail in real test
    pass


# OK: design() at module level
# Create design at module level
test_design = design()
test_design.provide("user_service_fixture", lambda: "mock_user_service")
test_design.provide("database_fixture", lambda: {"users": []})

# Register as pytest fixtures
register_fixtures_from_design(test_design)


# OK: test function using fixtures
def test_correct_usage(user_service_fixture, database_fixture):
    # Now user_service_fixture and database_fixture are available as fixtures
    assert user_service_fixture == "mock_user_service"
    assert isinstance(database_fixture, dict)


# OK: helper function (not a test)
def helper_function():
    # Helper functions can use design()
    with design() as d:
        d.provide("something", lambda: "value")
    return d


# OK: non-test function
def setup_application():
    # This is not a test function, so design() is allowed
    with design() as d:
        d.provide("app_service", lambda: "mock_app_service")
        d.provide("database", lambda: "mock_database")
    return d


# VIOLATION: nested design() in test
def test_nested_violation():
    def setup_test_data():
        with design() as d:
            d.provide("test_data_service", lambda: "mock_test_data")
        return d

    # This should still be detected
    setup_test_data()


# VIOLATION: conditional design() in test
@pytest.mark.skipif(True, reason="Skip")
def test_conditional_violation():
    some_condition = True
    if some_condition:
        with design() as d:
            d.provide("mock_service", lambda: "mock")
    else:
        with design() as d:
            d.provide("real_service", lambda: "real")


# VIOLATION: using pinjected module import
def test_module_import_violation():
    with pinjected.design() as d:
        d.provide("service", lambda: "mock_service")

    # This would fail in real test
    pass


# OK: test class with proper fixture usage
class TestUserService:
    def test_create_user(self, user_service_fixture):
        # Using fixture properly
        assert user_service_fixture == "mock_user_service"

    def test_delete_user(self, user_service_fixture, database_fixture):
        # Using fixtures properly
        assert user_service_fixture == "mock_user_service"
        assert isinstance(database_fixture, dict)
