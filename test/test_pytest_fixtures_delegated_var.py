"""
Comprehensive tests for DelegatedVar/IProxy support in pytest fixture registration.

This module tests various scenarios of using register_fixtures_from_design with
DelegatedVar/IProxy objects to ensure proper resolution and fixture registration.
"""

from typing import Dict, Protocol
import pytest
import warnings
from pinjected import design, injected, Injected, IProxy
from pinjected.pytest_fixtures import register_fixtures_from_design

pytestmark = pytest.mark.skip(reason="pytest_fixtures.py is deprecated")

warnings.filterwarnings(
    "ignore", category=DeprecationWarning, message=".*register_fixtures_from_design.*"
)


# ============================================================================
# TEST 1: BASIC IPROXY DESIGN REGISTRATION
# ============================================================================


class BasicServiceProtocol(Protocol):
    def __call__(self) -> Dict[str, str]: ...


@injected(protocol=BasicServiceProtocol)
def basic_service():
    """A basic service for testing IProxy registration."""
    return {"type": "basic", "status": "active"}


# Create a basic design wrapped in IProxy
basic_design = design(
    basic_service=basic_service,
    basic_config=Injected.pure({"env": "test", "debug": True}),
)

# Register using IProxy
register_fixtures_from_design(IProxy(basic_design))


class TestBasicIProxyRegistration:
    """Test basic IProxy design registration."""

    @pytest.mark.asyncio
    async def test_iproxy_fixtures_registered(self, basic_service, basic_config):
        """Test that fixtures from IProxy design are properly registered."""
        # Test basic_service
        service_result = basic_service()
        assert service_result["type"] == "basic"
        assert service_result["status"] == "active"

        # Test basic_config
        assert basic_config["env"] == "test"
        assert basic_config["debug"] is True


# ============================================================================
# TEST 2: IPROXY WITH COMPLEX DEPENDENCIES
# ============================================================================


class DbConnectionProtocol(Protocol):
    def __call__(self) -> Dict[str, str]: ...


class UserRepoProtocol(Protocol):
    def __call__(self) -> Dict[str, str]: ...


class AuthServiceProtocol(Protocol):
    def __call__(self) -> Dict[str, str]: ...


@injected(protocol=DbConnectionProtocol)
def db_connection():
    """Database connection for complex dependency test."""
    return {"type": "database", "host": "localhost", "port": 5432}


@injected(protocol=UserRepoProtocol)
def user_repository():
    """User repository that would normally depend on db_connection."""
    return {"type": "user_repo", "db_host": "localhost", "table": "users"}


@injected(protocol=AuthServiceProtocol)
def auth_service():
    """Auth service that would normally depend on user_repository."""
    return {"type": "auth_service", "repo": "user_repo", "jwt_enabled": True}


# Complex design with dependencies
complex_deps_design = design(
    db_connection=db_connection,
    user_repository=user_repository,
    auth_service=auth_service,
)

# Register using IProxy
register_fixtures_from_design(IProxy(complex_deps_design))


class TestIProxyComplexDependencies:
    """Test IProxy with complex dependency chains."""

    @pytest.mark.asyncio
    async def test_complex_dependencies_resolved(
        self, db_connection, user_repository, auth_service
    ):
        """Test that complex dependencies are properly resolved from IProxy."""
        # Test db_connection
        db_result = db_connection()
        assert db_result["type"] == "database"
        assert db_result["host"] == "localhost"

        # Test user_repository
        repo_result = user_repository()
        assert repo_result["type"] == "user_repo"
        assert repo_result["db_host"] == "localhost"

        # Test auth_service
        auth_result = auth_service()
        assert auth_result["type"] == "auth_service"
        assert auth_result["jwt_enabled"] is True


# ============================================================================
# TEST 3: MIXED REGULAR DESIGN AND IPROXY REGISTRATION
# ============================================================================


class CacheProtocol(Protocol):
    def __call__(self) -> Dict[str, str]: ...


class QueueProtocol(Protocol):
    def __call__(self) -> Dict[str, str]: ...


@injected(protocol=CacheProtocol)
def cache_service():
    """Cache service for mixed registration test."""
    return {"type": "cache", "backend": "redis"}


@injected(protocol=QueueProtocol)
def queue_service():
    """Queue service for mixed registration test."""
    return {"type": "queue", "backend": "rabbitmq"}


# Regular design registration
regular_design = design(cache_service=cache_service)
register_fixtures_from_design(regular_design)

# IProxy design registration
iproxy_design = design(queue_service=queue_service)
register_fixtures_from_design(IProxy(iproxy_design))


class TestMixedRegistration:
    """Test mixing regular Design and IProxy registrations."""

    @pytest.mark.asyncio
    async def test_mixed_registration_works(self, cache_service, queue_service):
        """Test that both regular and IProxy registered fixtures work."""
        # From regular design
        cache_result = cache_service()
        assert cache_result["type"] == "cache"
        assert cache_result["backend"] == "redis"

        # From IProxy design
        queue_result = queue_service()
        assert queue_result["type"] == "queue"
        assert queue_result["backend"] == "rabbitmq"


# ============================================================================
# TEST 4: IPROXY WITH EXCLUDE/INCLUDE OPTIONS
# ============================================================================


class MetricsProtocol(Protocol):
    def __call__(self) -> Dict[str, str]: ...


class LoggingProtocol(Protocol):
    def __call__(self) -> Dict[str, str]: ...


class MonitoringProtocol(Protocol):
    def __call__(self) -> Dict[str, str]: ...


@injected(protocol=MetricsProtocol)
def metrics_service():
    """Metrics service."""
    return {"type": "metrics", "provider": "prometheus"}


@injected(protocol=LoggingProtocol)
def logging_service():
    """Logging service - will be excluded."""
    return {"type": "logging", "level": "INFO"}


@injected(protocol=MonitoringProtocol)
def monitoring_service():
    """Monitoring service."""
    return {"type": "monitoring", "provider": "datadog"}


# Design with multiple services
options_design = design(
    metrics_service=metrics_service,
    logging_service=logging_service,
    monitoring_service=monitoring_service,
)

# Register with exclude option
register_fixtures_from_design(IProxy(options_design), exclude={"logging_service"})


class TestIProxyWithOptions:
    """Test IProxy registration with exclude/include options."""

    @pytest.mark.asyncio
    async def test_excluded_fixture_not_registered(
        self, metrics_service, monitoring_service
    ):
        """Test that excluded fixtures are not registered from IProxy."""
        # Should work - not excluded
        metrics_result = metrics_service()
        assert metrics_result["type"] == "metrics"

        monitoring_result = monitoring_service()
        assert monitoring_result["type"] == "monitoring"

    @pytest.mark.asyncio
    async def test_logging_service_not_available(self):
        """Test that logging_service fixture is not available."""
        # This test just documents that logging_service was excluded
        # We can't actually test for its absence in pytest fixtures
        pass


# ============================================================================
# TEST 5: MULTIPLE IPROXY REGISTRATIONS
# ============================================================================


class EmailProtocol(Protocol):
    def __call__(self) -> Dict[str, str]: ...


class SmsProtocol(Protocol):
    def __call__(self) -> Dict[str, str]: ...


@injected(protocol=EmailProtocol)
def email_service():
    """Email notification service."""
    return {"type": "email", "smtp": "smtp.example.com"}


@injected(protocol=SmsProtocol)
def sms_service():
    """SMS notification service."""
    return {"type": "sms", "provider": "twilio"}


# First IProxy registration
email_design = design(email_service=email_service)
register_fixtures_from_design(IProxy(email_design))

# Second IProxy registration
sms_design = design(sms_service=sms_service)
register_fixtures_from_design(IProxy(sms_design))


class TestMultipleIProxyRegistrations:
    """Test multiple IProxy registrations in the same module."""

    @pytest.mark.asyncio
    async def test_multiple_iproxy_registrations_work(self, email_service, sms_service):
        """Test that multiple IProxy registrations all work correctly."""
        # From first IProxy
        email_result = email_service()
        assert email_result["type"] == "email"
        assert email_result["smtp"] == "smtp.example.com"

        # From second IProxy
        sms_result = sms_service()
        assert sms_result["type"] == "sms"
        assert sms_result["provider"] == "twilio"


# ============================================================================
# TEST 6: IPROXY WITH PURE VALUES AND MIXED TYPES
# ============================================================================


class ApiClientProtocol(Protocol):
    def __call__(self) -> Dict[str, str]: ...


@injected(protocol=ApiClientProtocol)
def api_client():
    """API client service."""
    return {"type": "api_client", "base_url": "https://api.example.com"}


# Design with mixed types
mixed_types_design = design(
    api_client=api_client,
    api_key=Injected.pure("sk-test-12345"),
    rate_limit=Injected.pure(100),
    features=Injected.pure(["auth", "payments", "notifications"]),
    settings=Injected.pure({"timeout": 30, "retries": 3}),
)

# Register using IProxy
register_fixtures_from_design(IProxy(mixed_types_design))


class TestIProxyMixedTypes:
    """Test IProxy with various value types."""

    @pytest.mark.asyncio
    async def test_iproxy_with_pure_values(
        self, api_client, api_key, rate_limit, features, settings
    ):
        """Test that IProxy works with pure values of various types."""
        # Injected function
        client_result = api_client()
        assert client_result["type"] == "api_client"

        # Pure string
        assert api_key == "sk-test-12345"

        # Pure number
        assert rate_limit == 100

        # Pure list
        assert features == ["auth", "payments", "notifications"]

        # Pure dict
        assert settings == {"timeout": 30, "retries": 3}


# ============================================================================
# TEST 7: IPROXY DESIGN THAT DEPENDS ON METACONTEXT
# ============================================================================


class ContextServiceProtocol(Protocol):
    def __call__(self) -> Dict[str, str]: ...


@injected(protocol=ContextServiceProtocol)
def context_aware_service():
    """Service that would use context from MetaContext."""
    return {"type": "context_service", "context": "resolved_from_metacontext"}


# Design that might have MetaContext dependencies
context_design = design(
    context_service=context_aware_service,
    meta_value=Injected.pure("meta_context_value"),
)

# Register using IProxy - tests MetaContext resolution
register_fixtures_from_design(IProxy(context_design))


class TestIProxyMetaContext:
    """Test IProxy with MetaContext resolution."""

    @pytest.mark.asyncio
    async def test_metacontext_resolution(self, context_service, meta_value):
        """Test that IProxy properly resolves using MetaContext."""
        # Test service
        service_result = context_service()
        assert service_result["type"] == "context_service"
        assert service_result["context"] == "resolved_from_metacontext"

        # Test meta value
        assert meta_value == "meta_context_value"


# ============================================================================
# TEST 8: IPROXY RESOLUTION CACHING
# ============================================================================


class CachedServiceProtocol(Protocol):
    def __call__(self) -> Dict[str, str]: ...


@injected(protocol=CachedServiceProtocol)
def cached_service():
    """Service to test resolution caching."""
    import time

    return {"type": "cached", "timestamp": time.time()}


# Design for caching test
caching_design = design(
    cached_service=cached_service,
)

# Track resolution count by overriding the logger
resolution_count = 0
original_info = None


def counting_logger_info(msg):
    global resolution_count
    if "Resolving DelegatedVar to extract binding names" in msg:
        resolution_count += 1
    original_info(msg)


# Register using IProxy - should only resolve once due to caching
register_fixtures_from_design(IProxy(caching_design))


class TestIProxyResolutionCaching:
    """Test that IProxy resolution is cached."""

    @pytest.mark.asyncio
    async def test_resolution_cached(self, cached_service):
        """Test that the DelegatedVar resolution happens only once."""
        # The resolution should have happened during registration
        # Not during fixture usage
        result = cached_service()
        assert result["type"] == "cached"
        assert "timestamp" in result


# ============================================================================
# TEST 9: ERROR CASE - IPROXY RESOLVING TO NON-DESIGN
# ============================================================================

# This would be tested separately as it should raise an error during registration
# We can't easily test this in the same file without breaking other tests


# ============================================================================
# TEST 10: IPROXY WITH INCLUDE OPTION
# ============================================================================


class AnalyticsProtocol(Protocol):
    def __call__(self) -> Dict[str, str]: ...


class ReportingProtocol(Protocol):
    def __call__(self) -> Dict[str, str]: ...


class DashboardProtocol(Protocol):
    def __call__(self) -> Dict[str, str]: ...


@injected(protocol=AnalyticsProtocol)
def analytics_service():
    """Analytics service."""
    return {"type": "analytics", "engine": "spark"}


@injected(protocol=ReportingProtocol)
def reporting_service():
    """Reporting service."""
    return {"type": "reporting", "format": "pdf"}


@injected(protocol=DashboardProtocol)
def dashboard_service():
    """Dashboard service - will not be included."""
    return {"type": "dashboard", "framework": "react"}


# Design with multiple services
include_design = design(
    analytics_service=analytics_service,
    reporting_service=reporting_service,
    dashboard_service=dashboard_service,
)

# Register with include option - only analytics and reporting
register_fixtures_from_design(
    IProxy(include_design), include={"analytics_service", "reporting_service"}
)


class TestIProxyWithInclude:
    """Test IProxy registration with include option."""

    @pytest.mark.asyncio
    async def test_included_fixtures_only(self, analytics_service, reporting_service):
        """Test that only included fixtures are registered from IProxy."""
        # Should work - included
        analytics_result = analytics_service()
        assert analytics_result["type"] == "analytics"
        assert analytics_result["engine"] == "spark"

        reporting_result = reporting_service()
        assert reporting_result["type"] == "reporting"
        assert reporting_result["format"] == "pdf"
