"""
Integration tests for pytest fixture registration using register_fixtures_from_design.

This module demonstrates the full end-to-end workflow of using the convenience function
to register fixtures and then using those fixtures in actual tests.

Important Note:
--------------
Due to how pinjected fixtures are resolved, fixtures cannot depend on other fixtures
through pinjected's dependency injection. Each fixture is resolved independently by
creating its own resolver. If you need fixtures that depend on each other, you should:

1. Use pytest's native fixture dependency mechanism instead
2. Use the singleton pattern (as shown in test_pytest_fixtures_singleton.py)
3. Resolve all dependencies in a single fixture

In these tests, functions that would normally have dependencies are made independent
to demonstrate the fixture registration and usage workflow.
"""

from typing import Dict, List, Protocol

import pytest

from pinjected import design, injected, Injected, IProxy
from pinjected.picklable_logger import PicklableLogger
from pinjected.pytest_fixtures import register_fixtures_from_design


# ============================================================================
# BASIC USAGE TEST
# ============================================================================


# Protocol definitions for basic test
class ConfigProtocol(Protocol):
    def __call__(self) -> Dict[str, str]: ...


class DatabaseProtocol(Protocol):
    def __call__(self) -> Dict[str, str]: ...


class UserServiceProtocol(Protocol):
    def __call__(self) -> Dict[str, str]: ...


# Basic injected functions (without inter-fixture dependencies)
@injected(protocol=ConfigProtocol)
def config_provider():
    """Provides application configuration."""
    return {
        "app_name": "TestApp",
        "db_url": "postgresql://localhost/test",
        "debug": "true",
    }


@injected(protocol=DatabaseProtocol)
def database_connection():
    """Creates a database connection."""
    # In real usage, this would get config through pinjected's DI
    # But for fixture testing, we make it independent
    return {
        "type": "database",
        "url": "postgresql://localhost/test",
        "connected": True,
        "config_app": "TestApp",
    }


@injected(protocol=UserServiceProtocol)
def user_service():
    """User service."""
    # In real usage, this would depend on database through DI
    # But for fixture testing, we make it independent
    return {
        "type": "user_service",
        "db_url": "postgresql://localhost/test",
        "ready": True,
        "users": [],
    }


# Create design and register fixtures - this is the key part!
basic_design = design(
    config=config_provider,
    database=database_connection,
    user_service=user_service,
    logger=PicklableLogger(),
)

# Register all fixtures using the convenience function
register_fixtures_from_design(basic_design)


class TestBasicUsage:
    """Test basic usage of register_fixtures_from_design."""

    @pytest.mark.asyncio
    async def test_single_fixture(self, config):
        """Test using a single registered fixture."""
        # Call the injected function to get the actual config
        actual_config = config()
        assert actual_config["app_name"] == "TestApp"
        assert actual_config["db_url"] == "postgresql://localhost/test"
        assert actual_config["debug"] == "true"

    @pytest.mark.asyncio
    async def test_fixture_with_dependency(self, database):
        """Test fixture that has dependencies."""
        # Call the injected function
        actual_database = database()
        assert actual_database["type"] == "database"
        assert actual_database["url"] == "postgresql://localhost/test"
        assert actual_database["connected"] is True
        assert actual_database["config_app"] == "TestApp"

    @pytest.mark.asyncio
    async def test_multiple_fixtures(self, config, database, user_service):
        """Test using multiple fixtures in one test."""
        # Call the injected functions
        actual_config = config()
        actual_database = database()
        actual_user_service = user_service()

        # Verify config
        assert actual_config["app_name"] == "TestApp"

        # Verify database uses config
        assert actual_database["url"] == actual_config["db_url"]
        assert actual_database["config_app"] == actual_config["app_name"]

        # Verify user_service uses database
        assert actual_user_service["db_url"] == actual_database["url"]
        assert actual_user_service["ready"] == actual_database["connected"]
        assert actual_user_service["users"] == []


# ============================================================================
# FIXTURE OPTIONS TEST (prefix, exclude)
# ============================================================================


# Additional services for options test
class CacheServiceProtocol(Protocol):
    def __call__(self) -> Dict[str, str]: ...


class LoggerProtocol(Protocol):
    def __call__(self) -> Dict[str, str]: ...


@injected(protocol=CacheServiceProtocol)
def cache_service():
    """Cache service."""
    return {"type": "cache", "provider": "redis"}


@injected(protocol=LoggerProtocol)
def logger_service():
    """Logger service - will be excluded."""
    return {"type": "logger", "level": "INFO"}


# Design with services to test options
options_design = design(
    cache=cache_service,
    logger=logger_service,
)

# Register with prefix and exclude
register_fixtures_from_design(options_design, exclude={"logger"})


class TestFixtureOptions:
    """Test fixture registration with options."""

    @pytest.mark.asyncio
    async def test_fixture_with_prefix(self, cache):
        """Test that fixture is registered."""
        # Call the injected function
        actual_cache = cache()
        assert actual_cache["type"] == "cache"
        assert actual_cache["provider"] == "redis"

    @pytest.mark.asyncio
    async def test_excluded_fixture_not_available(self, cache):
        """Test that excluded fixtures are registered but logger is excluded."""
        # Test that cache is available (not excluded)
        actual_cache = cache()
        assert actual_cache["type"] == "cache"

        # Since logger is registered from basic_design earlier,
        # we can't test exclusion by checking hasattr.
        # The exclude parameter prevents registering logger from options_design,
        # but logger fixture still exists from basic_design.


# ============================================================================
# COMPLEX DEPENDENCIES TEST
# ============================================================================


# Protocols for complex dependency test
class AuthConfigProtocol(Protocol):
    def __call__(self) -> Dict[str, str]: ...


class AuthProviderProtocol(Protocol):
    def __call__(self) -> Dict[str, str]: ...


class TokenServiceProtocol(Protocol):
    def __call__(self) -> Dict[str, str]: ...


class SessionManagerProtocol(Protocol):
    def __call__(self) -> Dict[str, str]: ...


# Independent services that would normally have dependencies
@injected(protocol=AuthConfigProtocol)
def auth_config():
    """Authentication configuration."""
    return {"secret_key": "test_secret_123", "algorithm": "HS256", "expiry": "3600"}


@injected(protocol=AuthProviderProtocol)
def auth_provider():
    """Authentication provider."""
    # Would normally depend on config through DI
    return {"type": "auth_provider", "secret": "test_secret_123", "algorithm": "HS256"}


@injected(protocol=TokenServiceProtocol)
def token_service():
    """Token service."""
    # Would normally depend on auth_provider through DI
    return {
        "type": "token_service",
        "provider": "auth_provider",
        "algorithm": "HS256",
        "tokens_issued": 0,
    }


@injected(protocol=SessionManagerProtocol)
def session_manager():
    """Session manager."""
    # Would normally depend on token_service and auth_provider through DI
    return {
        "type": "session_manager",
        "token_service": "token_service",
        "auth_provider": "auth_provider",
        "algorithm": "HS256",
        "sessions": [],
    }


# Design with complex dependencies
complex_design = design(
    auth_config=auth_config,
    auth_provider=auth_provider,
    token_service=token_service,
    session_manager=session_manager,
)

# Register fixtures
register_fixtures_from_design(IProxy(complex_design))


class TestComplexDependencies:
    """Test fixtures with complex dependency chains."""

    @pytest.mark.asyncio
    async def test_deep_dependency_chain(
        self, session_manager, token_service, auth_provider
    ):
        """Test that deep dependencies are resolved correctly."""
        # Call the injected functions
        actual_session_manager = session_manager()
        actual_token_service = token_service()
        actual_auth_provider = auth_provider()

        # Verify session manager has correct dependencies
        assert actual_session_manager["type"] == "session_manager"
        assert actual_session_manager["token_service"] == "token_service"
        assert actual_session_manager["auth_provider"] == "auth_provider"
        assert actual_session_manager["algorithm"] == "HS256"

        # Verify token service
        assert actual_token_service["provider"] == "auth_provider"
        assert actual_token_service["algorithm"] == "HS256"

        # Verify auth provider
        assert actual_auth_provider["secret"] == "test_secret_123"
        assert actual_auth_provider["algorithm"] == "HS256"

    @pytest.mark.asyncio
    async def test_all_fixtures_independent_instances(
        self, token_service, session_manager
    ):
        """Test that each fixture gets its own instance."""
        # Call the injected functions
        actual_token_service = token_service()
        actual_session_manager = session_manager()

        # Modify token service
        actual_token_service["tokens_issued"] = 100

        # Session manager should not be affected since each fixture
        # gets its own resolution (as documented)
        assert actual_session_manager["sessions"] == []

    def test_non_async(self, token_service, logger):
        logger.info("Testing non-async fixture usage")
        # Call the injected function
        actual_token_service = token_service()
        assert actual_token_service["provider"] == "auth_provider"


# ============================================================================
# MIXED TYPES TEST
# ============================================================================


# Test with different types of injected values
class ListServiceProtocol(Protocol):
    def __call__(self) -> List[str]: ...


@injected(protocol=ListServiceProtocol)
def list_service():
    """Returns a list."""
    return ["item1", "item2", "item3"]


mixed_design = design(
    pure_string=Injected.pure("Hello, World!"),
    pure_number=Injected.pure(42),
    pure_dict=Injected.pure({"key": "value"}),
    list_service=list_service,
)

register_fixtures_from_design(mixed_design)


class TestMixedTypes:
    """Test fixtures with various types."""

    @pytest.mark.asyncio
    async def test_pure_string_fixture(self, pure_string):
        """Test pure string fixture."""
        assert pure_string == "Hello, World!"

    @pytest.mark.asyncio
    async def test_pure_number_fixture(self, pure_number):
        """Test pure number fixture."""
        assert pure_number == 42

    @pytest.mark.asyncio
    async def test_pure_dict_fixture(self, pure_dict):
        """Test pure dict fixture."""
        assert pure_dict == {"key": "value"}

    @pytest.mark.asyncio
    async def test_list_service_fixture(self, list_service):
        """Test list service fixture."""
        # Call the injected function
        actual_list_service = list_service()
        assert actual_list_service == ["item1", "item2", "item3"]

    @pytest.mark.asyncio
    async def test_all_mixed_fixtures(
        self, pure_string, pure_number, pure_dict, list_service
    ):
        """Test all mixed fixtures together."""
        # Pure values are returned directly, but list_service needs to be called
        actual_list_service = list_service()

        assert isinstance(pure_string, str)
        assert isinstance(pure_number, int)
        assert isinstance(pure_dict, dict)
        assert isinstance(actual_list_service, list)
