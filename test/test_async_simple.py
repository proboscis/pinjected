"""Simple async tests for pinjected using AsyncResolver."""

import pytest
import asyncio
import sys
from typing import Protocol
from pinjected import instance, injected, design, AsyncResolver

# Use the appropriate ExceptionGroup based on Python version
if sys.version_info >= (3, 11):
    # Python 3.11+ has native ExceptionGroup
    from builtins import BaseExceptionGroup

    ExceptionGroup = BaseExceptionGroup
else:
    # Python < 3.11 uses our compatibility ExceptionGroup
    from pinjected.compatibility.task_group import ExceptionGroup


class AsyncGreeterProtocol(Protocol):
    async def __call__(self, name: str) -> str: ...


def test_async_instance_with_resolver():
    """Test async @instance with AsyncResolver."""

    @instance
    async def async_config():
        await asyncio.sleep(0.01)
        return {"host": "localhost", "port": 5432}

    d = design()
    resolver = AsyncResolver(d)

    # Use blocking resolver to avoid event loop issues
    blocking = resolver.to_blocking()
    config = blocking.provide(async_config)

    assert config["host"] == "localhost"
    assert config["port"] == 5432


def test_async_injected_with_resolver():
    """Test async @injected with a_ prefix using AsyncResolver."""

    @instance
    def prefix():
        return "Hello"

    @injected(protocol=AsyncGreeterProtocol)
    async def a_greet(prefix, /, name: str) -> str:
        await asyncio.sleep(0.01)
        return f"{prefix}, {name}!"

    d = design()
    resolver = AsyncResolver(d)
    blocking = resolver.to_blocking()

    greet_func = blocking.provide(a_greet)
    # The blocking resolver handles async functions internally
    result = asyncio.run(greet_func("World"))
    assert result == "Hello, World!"


def test_mixed_sync_async():
    """Test mixing sync and async dependencies."""

    @instance
    def sync_config():
        return {"timeout": 30}

    @instance
    async def async_service():
        await asyncio.sleep(0.01)
        return "async_service_ready"

    @instance
    def combined(sync_config, async_service):
        return {"config": sync_config, "service": async_service}

    d = design()
    resolver = AsyncResolver(d)
    blocking = resolver.to_blocking()

    result = blocking.provide(combined)
    assert result["config"]["timeout"] == 30
    assert result["service"] == "async_service_ready"


def test_async_singleton_behavior():
    """Test that async @instance behaves as singleton."""
    counter = 0

    @instance
    async def expensive_async_service():
        nonlocal counter
        counter += 1
        await asyncio.sleep(0.01)
        return f"service_{counter}"

    d = design()
    resolver = AsyncResolver(d)
    blocking = resolver.to_blocking()

    # Multiple calls should return the same instance
    service1 = blocking.provide(expensive_async_service)
    service2 = blocking.provide(expensive_async_service)

    assert service1 == "service_1"
    assert service2 == "service_1"  # Same instance
    assert counter == 1  # Only initialized once


def test_async_error_handling():
    """Test error propagation in async functions."""

    @instance
    async def failing_service():
        await asyncio.sleep(0.01)
        raise ValueError("Service initialization failed")

    d = design()
    resolver = AsyncResolver(d)
    blocking = resolver.to_blocking()

    # In Python 3.11+, TaskGroup raises the standard ExceptionGroup
    # which is a subclass of BaseExceptionGroup
    exception_type = ExceptionGroup

    with pytest.raises(exception_type) as excinfo:
        blocking.provide(failing_service)

    # Check that the ExceptionGroup contains the expected ValueError
    assert len(excinfo.value.exceptions) == 1
    assert isinstance(excinfo.value.exceptions[0], ValueError)
    assert "Service initialization failed" in str(excinfo.value.exceptions[0])


def test_async_injected_naming_convention():
    """Test that async @injected functions should have a_ prefix."""

    # Good practice - with a_ prefix
    @injected
    async def a_fetch_data(api_client, /, url: str) -> dict:
        await asyncio.sleep(0.01)
        return {"url": url, "data": "fetched"}

    # Bad practice - without a_ prefix (but still works)
    @injected
    async def fetch_data_bad(api_client, /, url: str) -> dict:
        await asyncio.sleep(0.01)
        return {"url": url, "data": "fetched"}

    d = design(api_client="mock_client")
    resolver = AsyncResolver(d)
    blocking = resolver.to_blocking()

    # Both work, but a_ prefix is the convention
    good_func = blocking.provide(a_fetch_data)
    bad_func = blocking.provide(fetch_data_bad)

    result1 = asyncio.run(good_func("https://example.com"))
    result2 = asyncio.run(bad_func("https://example.com"))

    assert result1["data"] == "fetched"
    assert result2["data"] == "fetched"


def test_async_with_design_context():
    """Test async with design context override."""

    @instance
    async def service(mode):
        await asyncio.sleep(0.01)
        return f"Service in {mode} mode"

    base_design = design(mode="production")

    # Normal execution
    resolver1 = AsyncResolver(base_design)
    blocking1 = resolver1.to_blocking()
    assert blocking1.provide(service) == "Service in production mode"

    # With override
    test_design = base_design + design(mode="testing")
    resolver2 = AsyncResolver(test_design)
    blocking2 = resolver2.to_blocking()
    assert blocking2.provide(service) == "Service in testing mode"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
