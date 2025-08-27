"""Simple tests for design() functionality that work with the actual API."""

import pytest
from pinjected import (
    design,
    instance,
    injected,
    Injected,
    classes,
    instances,
    providers,
)
from typing import Protocol


def test_design_basic():
    """Test basic design() functionality."""
    d = design(host="localhost", port=5432, debug=True)

    # Use provide method directly on design
    assert d.provide("host") == "localhost"
    assert d.provide("port") == 5432
    assert d.provide("debug") is True


def test_design_combination():
    """Test combining multiple designs with + operator."""
    base_design = design(host="localhost", port=5432, username="admin")

    dev_design = design(debug=True, log_level="DEBUG")

    prod_design = design(
        debug=False,
        log_level="ERROR",
        port=443,  # Override port
    )

    # Combine designs - later values override earlier ones
    dev_config = base_design + dev_design
    prod_config = base_design + prod_design

    assert dev_config.provide("host") == "localhost"
    assert dev_config.provide("port") == 5432  # From base
    assert dev_config.provide("debug") is True
    assert dev_config.provide("log_level") == "DEBUG"

    assert prod_config.provide("host") == "localhost"
    assert prod_config.provide("port") == 443  # Overridden
    assert prod_config.provide("debug") is False


def test_design_with_instance():
    """Test design with @instance functions."""

    @instance
    def database_url(host, port, username):
        return f"postgresql://{username}@{host}:{port}/db"

    d = design(
        host="localhost",
        port=5432,
        username="admin",
        # Can directly include instance functions
        database_url=database_url,
    )

    assert d.provide("database_url") == "postgresql://admin@localhost:5432/db"


def test_design_with_injected():
    """Test design with @injected functions."""

    class GreeterProtocol(Protocol):
        def __call__(self, name: str) -> str: ...

    @injected(protocol=GreeterProtocol)
    def greet(prefix, /, name: str) -> str:
        return f"{prefix} {name}!"

    d = design(
        prefix="Hello",
        greet=greet,  # Can include injected functions
    )

    greet_func = d.provide("greet")
    assert greet_func("World") == "Hello World!"


def test_instances_helper():
    """Test instances() helper function."""
    d = instances(api_key="secret123", max_retries=3, timeout=30.0)

    assert d.provide("api_key") == "secret123"
    assert d.provide("max_retries") == 3
    assert d.provide("timeout") == 30.0


def test_classes_helper():
    """Test classes() helper function."""

    class Config:
        def __init__(self, host, port):
            self.host = host
            self.port = port

        def to_url(self):
            return f"http://{self.host}:{self.port}"

    d = design(host="localhost", port=8080) + classes(config=Config)

    config = d.provide("config")
    assert isinstance(config, Config)
    assert config.to_url() == "http://localhost:8080"


def test_providers_helper():
    """Test providers() helper function."""

    def create_connection_string(host, port, username):
        return f"{username}@{host}:{port}"

    d = design(host="localhost", port=5432, username="admin") + providers(
        connection_string=create_connection_string
    )

    assert d.provide("connection_string") == "admin@localhost:5432"


def test_injected_by_name():
    """Test creating Injected instances by name."""
    my_value = Injected.by_name("my_value")

    d = design(my_value=42)
    assert d.provide(my_value) == 42


def test_injected_map():
    """Test Injected.map() functionality."""
    base = Injected.by_name("base")
    doubled = base.map(lambda x: x * 2)
    squared = base.map(lambda x: x**2)

    d = design(base=5)
    assert d.provide(doubled) == 10
    assert d.provide(squared) == 25


def test_injected_pure():
    """Test Injected.pure() for constant values."""
    pure_value = Injected.pure(42)

    d = design()  # No dependencies needed
    assert d.provide(pure_value) == 42


def test_design_with_injected_instances():
    """Test design with Injected instances."""
    # Create an Injected that depends on other values
    connection = Injected.bind(lambda host, port: f"{host}:{port}")

    d = design(host="localhost", port=8080, connection=connection)

    assert d.provide("connection") == "localhost:8080"


def test_design_contains():
    """Test checking if a key is in design."""
    d = design(a=1, b=2)

    from pinjected.v2.keys import StrBindKey

    assert StrBindKey("a") in d
    assert StrBindKey("b") in d
    assert StrBindKey("c") not in d


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
