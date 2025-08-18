"""Tests for @instance decorator functionality."""

import pytest
import sys
from pinjected import instance, design, Injected

# Use the appropriate ExceptionGroup based on Python version
if sys.version_info >= (3, 11):
    # Python 3.11+ has native ExceptionGroup
    ExceptionGroup = BaseExceptionGroup  # noqa: F821
else:
    # Python < 3.11 uses our compatibility ExceptionGroup
    from pinjected.compatibility.task_group import ExceptionGroup


def test_instance_basic():
    """Test basic @instance functionality."""

    @instance
    def database_connection():
        return "connected"

    d = design()
    g = d.to_graph()

    # @instance returns a DelegatedVar which can be used for dependency injection
    # No need to assert type - just test functionality

    # Resolve the instance
    result = g.provide(database_connection)
    assert result == "connected"


def test_instance_with_dependencies():
    """Test @instance with dependency injection."""

    @instance
    def config():
        return {"host": "localhost", "port": 5432}

    @instance
    def database_connection(config):
        return f"connected to {config['host']}:{config['port']}"

    d = design()
    g = d.to_graph()

    result = g.provide(database_connection)
    assert result == "connected to localhost:5432"


def test_instance_singleton_behavior():
    """Test that @instance behaves as singleton."""
    counter = 0

    @instance
    def expensive_service():
        nonlocal counter
        counter += 1
        return f"service_{counter}"

    d = design()
    g = d.to_graph()

    # Multiple calls should return the same instance
    result1 = g.provide(expensive_service)
    result2 = g.provide(expensive_service)

    assert result1 == "service_1"
    assert result2 == "service_1"  # Same instance
    assert counter == 1  # Only initialized once


def test_instance_with_design_overrides():
    """Test overriding dependencies in design."""

    @instance
    def logger():
        return "default_logger"

    @instance
    def service(logger):
        return f"service with {logger}"

    # Default design
    d1 = design()
    g1 = d1.to_graph()
    assert g1.provide(service) == "service with default_logger"

    # Override logger
    d2 = design(logger="custom_logger")
    g2 = d2.to_graph()
    assert g2.provide(service) == "service with custom_logger"


def test_instance_with_multiple_dependencies():
    """Test @instance with multiple dependencies."""

    @instance
    def host():
        return "localhost"

    @instance
    def port():
        return 5432

    @instance
    def username():
        return "admin"

    @instance
    def database_url(host, port, username):
        return f"postgresql://{username}@{host}:{port}/db"

    d = design()
    g = d.to_graph()

    result = g.provide(database_url)
    assert result == "postgresql://admin@localhost:5432/db"


def test_instance_naming_convention():
    """Test that @instance functions should be nouns."""

    # Good examples - nouns
    @instance
    def database():
        return "db"

    @instance
    def cache_manager():
        return "cache"

    @instance
    def user_repository():
        return "repo"

    d = design()
    g = d.to_graph()

    assert g.provide(database) == "db"
    assert g.provide(cache_manager) == "cache"
    assert g.provide(user_repository) == "repo"


def test_instance_with_class():
    """Test @instance returning class instances."""

    class Database:
        def __init__(self, host, port):
            self.host = host
            self.port = port

        def connect(self):
            return f"Connected to {self.host}:{self.port}"

    @instance
    def database_config():
        return {"host": "localhost", "port": 5432}

    @instance
    def database(database_config):
        return Database(**database_config)

    d = design()
    g = d.to_graph()

    db = g.provide(database)
    assert isinstance(db, Database)
    assert db.connect() == "Connected to localhost:5432"


def test_instance_error_propagation():
    """Test error handling in @instance."""

    @instance
    def failing_service():
        raise ValueError("Service initialization failed")

    d = design()
    g = d.to_graph()

    with pytest.raises(ExceptionGroup) as excinfo:
        g.provide(failing_service)

    # Check that the ExceptionGroup contains the expected ValueError
    assert len(excinfo.value.exceptions) == 1
    assert isinstance(excinfo.value.exceptions[0], ValueError)
    assert "Service initialization failed" in str(excinfo.value.exceptions[0])


def test_instance_with_none_return():
    """Test @instance returning None."""

    @instance
    def optional_service():
        return None

    d = design()
    g = d.to_graph()

    result = g.provide(optional_service)
    assert result is None


def test_instance_circular_dependency():
    """Test handling of circular dependencies."""

    @instance
    def service_a(service_b):
        return f"A depends on {service_b}"

    @instance
    def service_b(service_a):
        return f"B depends on {service_a}"

    d = design()
    g = d.to_graph()

    # This should raise an error due to circular dependency
    with pytest.raises(Exception):
        g.provide(service_a)


def test_instance_with_injected_by_name():
    """Test using Injected.by_name with @instance."""

    @instance
    def database():
        return "database_instance"

    # Create an Injected reference by name
    db_ref = Injected.by_name("database")

    d = design()
    g = d.to_graph()

    # Both should resolve to the same value
    assert g.provide(database) == "database_instance"
    assert g.provide(db_ref) == "database_instance"


def test_instance_no_default_args():
    """Test that @instance functions should not have default arguments."""

    # This is an anti-pattern but should still work
    @instance
    def bad_instance(param="default"):
        return f"value: {param}"

    # Without providing param, it should use None (not the default)
    d = design()
    g = d.to_graph()

    # The default argument is ignored in dependency injection
    with pytest.raises(Exception):
        # This will fail because param is not provided
        g.provide(bad_instance)

    # Must provide the parameter explicitly
    d2 = design(param="provided")
    g2 = d2.to_graph()
    assert g2.provide(bad_instance) == "value: provided"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
