"""Tests for async support in pinjected."""

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


# Define async protocols
class AsyncDataFetcherProtocol(Protocol):
    async def __call__(self, id: str) -> dict: ...


class AsyncProcessorProtocol(Protocol):
    async def __call__(self, data: dict) -> str: ...


class AsyncMessageSenderProtocol(Protocol):
    async def __call__(self, message: str, channel: str = "general") -> bool: ...


def test_async_instance():
    """Test async @instance decorator (no a_ prefix needed)."""

    @instance
    async def database_connection():
        # Simulate async connection
        await asyncio.sleep(0.01)
        return {"connected": True, "host": "localhost"}

    @instance
    async def cache_connection():
        # Another async instance
        await asyncio.sleep(0.01)
        return {"type": "redis", "connected": True}

    d = design()
    resolver = AsyncResolver(d)
    blocking = resolver.to_blocking()

    # The blocking resolver handles async resolution automatically
    db = blocking.provide(database_connection)
    cache = blocking.provide(cache_connection)

    assert db["connected"] is True
    assert cache["type"] == "redis"


def test_async_injected_with_a_prefix():
    """Test async @injected with mandatory a_ prefix."""

    @instance
    def api_client():
        return {"base_url": "https://api.example.com"}

    @injected(protocol=AsyncDataFetcherProtocol)
    async def a_fetch_user(api_client, /, id: str) -> dict:
        # Simulate async API call
        await asyncio.sleep(0.01)
        return {"id": id, "name": f"User_{id}", "api": api_client["base_url"]}

    d = design()
    resolver = AsyncResolver(d)
    blocking = resolver.to_blocking()

    # Get the async function
    fetch_func = blocking.provide(a_fetch_user)

    # Call it with runtime argument
    result = asyncio.run(fetch_func("123"))
    assert result["id"] == "123"
    assert result["name"] == "User_123"
    assert result["api"] == "https://api.example.com"


def test_async_injected_calling_async_injected():
    """Test async @injected functions calling other async @injected functions."""

    @injected(protocol=AsyncDataFetcherProtocol)
    async def a_fetch_data(database, /, id: str) -> dict:
        await asyncio.sleep(0.01)
        return {"id": id, "data": f"content_{id}"}

    @injected(protocol=AsyncProcessorProtocol)
    async def a_process_data(logger, /, data: dict) -> str:
        await asyncio.sleep(0.01)
        return f"Processed: {data['data']}"

    @injected(protocol=AsyncMessageSenderProtocol)
    async def a_handle_request(
        a_fetch_data: AsyncDataFetcherProtocol,  # Must declare with Protocol
        a_process_data: AsyncProcessorProtocol,  # Must declare with Protocol
        message_queue,
        /,
        message: str,
        channel: str = "general",
    ) -> bool:
        # Extract ID from message
        msg_id = message.split(":")[-1]

        # Call other async @injected functions
        data = await a_fetch_data(msg_id)
        processed = await a_process_data(data)

        # Use injected service
        await message_queue.send(processed, channel)
        return True

    @instance
    def database():
        return "mock_db"

    @instance
    def logger():
        return "mock_logger"

    @instance
    def message_queue():
        class MockQueue:
            async def send(self, msg, channel):
                await asyncio.sleep(0.01)
                return True

        return MockQueue()

    d = design()
    resolver = AsyncResolver(d)
    blocking = resolver.to_blocking()

    handler = blocking.provide(a_handle_request)
    result = asyncio.run(handler("process:42"))
    assert result is True


def test_mixing_sync_and_async():
    """Test mixing synchronous and async dependencies."""

    @instance
    def config():
        return {"timeout": 30, "retries": 3}

    @instance
    def logger():
        return "sync_logger"

    @instance
    async def async_client():
        await asyncio.sleep(0.01)
        return {"client": "async_http"}

    @injected(protocol=AsyncDataFetcherProtocol)
    async def a_fetch_with_retry(
        config,  # Sync dependency
        logger,  # Sync dependency
        async_client,  # Async dependency (auto-resolved)
        /,
        id: str,
    ) -> dict:
        # Use sync config
        timeout = config["timeout"]

        # Use async client
        await asyncio.sleep(0.01)

        return {"id": id, "timeout": timeout, "client": async_client["client"]}

    d = design()
    resolver = AsyncResolver(d)
    blocking = resolver.to_blocking()

    fetch = blocking.provide(a_fetch_with_retry)
    result = asyncio.run(fetch("123"))

    assert result["timeout"] == 30
    assert result["client"] == "async_http"


def test_async_instance_singleton():
    """Test that async @instance also behaves as singleton."""
    counter = 0

    @instance
    async def expensive_async_service():
        nonlocal counter
        counter += 1
        await asyncio.sleep(0.01)
        return f"async_service_{counter}"

    d = design()
    resolver = AsyncResolver(d)
    blocking = resolver.to_blocking()

    # Multiple calls should return the same instance
    service1 = blocking.provide(expensive_async_service)
    service2 = blocking.provide(expensive_async_service)

    assert service1 == "async_service_1"
    assert service2 == "async_service_1"  # Same instance
    assert counter == 1  # Only initialized once


def test_async_error_propagation():
    """Test error handling in async functions."""

    @instance
    async def failing_async_service():
        await asyncio.sleep(0.01)
        raise ValueError("Async service failed")

    @injected(protocol=AsyncDataFetcherProtocol)
    async def a_use_failing_service(failing_async_service, /, id: str) -> dict:
        # This will fail when the service is resolved
        return {"service": failing_async_service, "id": id}

    d = design()
    resolver = AsyncResolver(d)
    blocking = resolver.to_blocking()

    # The error should propagate
    with pytest.raises(ExceptionGroup) as excinfo:
        blocking.provide(failing_async_service)

    # Check that the ExceptionGroup contains the expected ValueError
    assert len(excinfo.value.exceptions) == 1
    assert isinstance(excinfo.value.exceptions[0], ValueError)
    assert "Async service failed" in str(excinfo.value.exceptions[0])


def test_async_context_manager():
    """Test async context managers in dependencies."""

    class AsyncResource:
        def __init__(self):
            self.connected = False

        async def __aenter__(self):
            await asyncio.sleep(0.01)
            self.connected = True
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            await asyncio.sleep(0.01)
            self.connected = False

    @instance
    async def async_resource():
        # In real usage, this would be managed properly
        resource = AsyncResource()
        await resource.__aenter__()
        return resource

    d = design()
    resolver = AsyncResolver(d)
    blocking = resolver.to_blocking()

    resource = blocking.provide(async_resource)
    assert resource.connected is True


def test_async_generator():
    """Test async generator support."""

    @injected
    async def a_generate_data(config, /, count: int):
        prefix = config["prefix"]
        for i in range(count):
            await asyncio.sleep(0.01)
            yield f"{prefix}_{i}"

    d = design(config={"prefix": "item"})
    resolver = AsyncResolver(d)
    blocking = resolver.to_blocking()

    generator_func = blocking.provide(a_generate_data)

    # Collect results using asyncio.run
    async def collect_results():
        results = []
        async for item in generator_func(3):
            results.append(item)
        return results

    results = asyncio.run(collect_results())
    assert results == ["item_0", "item_1", "item_2"]


def test_parallel_dependency_resolution():
    """Test that independent async dependencies are resolved in parallel."""
    import time

    @instance
    async def slow_service_1():
        await asyncio.sleep(0.1)
        return "service1"

    @instance
    async def slow_service_2():
        await asyncio.sleep(0.1)
        return "service2"

    @instance
    async def slow_service_3():
        await asyncio.sleep(0.1)
        return "service3"

    @instance
    def combined_service(slow_service_1, slow_service_2, slow_service_3):
        return f"{slow_service_1},{slow_service_2},{slow_service_3}"

    d = design()
    resolver = AsyncResolver(d)
    blocking = resolver.to_blocking()

    # Should resolve in parallel, so total time ~0.1s, not 0.3s
    start = time.time()
    result = blocking.provide(combined_service)
    duration = time.time() - start

    assert result == "service1,service2,service3"
    # Allow some overhead, but should be much less than 0.3s
    assert duration < 0.2


def test_async_injected_without_a_prefix_fails():
    """Test that async @injected without a_ prefix is not recommended."""

    # This is bad practice - async @injected should have a_ prefix
    @injected  # Missing protocol too - double bad practice
    async def fetch_data(api, /, id: str):  # Missing a_ prefix!
        await asyncio.sleep(0.01)
        return {"id": id}

    # While this might work, it violates naming conventions
    # and makes it unclear that this is an async function
    d = design(api="mock_api")
    resolver = AsyncResolver(d)
    blocking = resolver.to_blocking()

    # It technically works but violates conventions
    func = blocking.provide(fetch_data)
    result = asyncio.run(func("123"))
    assert result["id"] == "123"

    # But this is NOT recommended - always use a_ prefix for async @injected


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
