"""Simple async tests for pinjected using AsyncResolver."""

import asyncio
from typing import Protocol
from pinjected import instance, injected, design, AsyncResolver

# Note: ExceptionGroup handling moved to test_core_async.py


class AsyncGreeterProtocol(Protocol):
    async def __call__(self, name: str) -> str: ...


# Removed duplicate tests - these are covered more comprehensively in test_core_async.py
# Keeping only unique tests that aren't in test_core_async.py


# Mock class for test
class ApiClient:
    pass


def test_async_injected_naming_convention():
    """Test that async @injected functions should have a_ prefix."""

    # Good practice - with a_ prefix


class FetchDataProtocol(Protocol):
    async def __call__(
        self,
    ) -> dict: ...


@injected(protocol=FetchDataProtocol)
async def a_fetch_data(api_client: "ApiClient", /, url: str) -> dict:
    await asyncio.sleep(0.01)
    return {"url": url, "data": "fetched"}

    # Bad practice - without a_ prefix (but still works)


class FetchDataBadProtocol(Protocol):
    async def __call__(
        self,
    ) -> dict: ...


@injected(protocol=FetchDataBadProtocol)
async def a_fetch_data_bad(api_client: "ApiClient", /, url: str) -> dict:
    await asyncio.sleep(0.01)
    return {"url": url, "data": "fetched"}

    d = design(api_client="mock_client")
    resolver = AsyncResolver(d)
    blocking = resolver.to_blocking()

    # Both work, but a_ prefix is the convention
    good_func = blocking.provide(a_fetch_data)
    bad_func = blocking.provide(a_fetch_data_bad)

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


# Removed __main__ block per PINJ019 rule
# Use: python -m pinjected run <module.function> instead
