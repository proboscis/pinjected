"""
Test file for issue #217: @async_cached decorator does not respect key_hashers parameter

This test file demonstrates the bug and will verify the fix.
"""

import asyncio

from injected_utils.injected_cache_utils import async_cached
from pinjected import instance, design, injected
from pinjected.test import injected_pytest


# Custom hashers for testing
def hash_user_id(user_id: str) -> str:
    """Custom hasher that only uses first 3 chars of user_id"""
    return user_id[:3]


def hash_timestamp(ts: int) -> str:
    """Custom hasher that rounds timestamp to nearest hour"""
    return str(ts // 3600)


# Create a cached function using @async_cached
@async_cached(cache=injected("test_cache"), key_hashers=injected("test_key_hashers"))
@instance
async def cached_fetch_user_data():
    """Factory that creates a cached fetch function"""
    call_count = 0

    async def _fetch(user_id: str, timestamp: int, include_details: bool = False):
        nonlocal call_count
        call_count += 1
        return {
            "user_id": user_id,
            "timestamp": timestamp,
            "include_details": include_details,
            "call_count": call_count,
        }

    return _fetch


# Test design with custom key hashers
test_design_with_hashers = design(
    test_cache={},
    test_key_hashers={"user_id": hash_user_id, "timestamp": hash_timestamp},
    cached_fetch_user_data=cached_fetch_user_data,
)


@injected_pytest(test_design_with_hashers)
async def test_async_cached_respects_key_hashers(cached_fetch_user_data):
    """
    Test that verifies custom key_hashers are properly applied to specific parameters.
    """
    # cached_fetch_user_data is the cached interface function
    # We need to call it to get the actual fetch function

    # Test 1: Same first 3 chars of user_id should hit cache
    result1 = await cached_fetch_user_data("user123", 1234567890, True)
    assert result1["call_count"] == 1
    assert result1["user_id"] == "user123"

    # This should hit cache because hash_user_id("user456") == hash_user_id("user123") == "use"
    result2 = await cached_fetch_user_data("user456", 1234567890, True)
    assert result2["call_count"] == 1  # Should hit cache due to custom hasher
    assert result2["user_id"] == "user123"  # Should return cached value from first call

    # Test 2: Different first 3 chars should miss cache
    result3 = await cached_fetch_user_data("abc123", 1234567890, True)
    assert result3["call_count"] == 2  # Should miss cache
    assert result3["user_id"] == "abc123"

    # Test 3: Same hour timestamp should hit cache
    # 1234567899 and 1234567890 both hash to same hour (342935)
    result4 = await cached_fetch_user_data("abc123", 1234567899, True)
    assert result4["call_count"] == 2  # Should hit cache due to custom hasher
    assert result4["timestamp"] == 1234567890  # Should return cached value from result3

    # Test 4: Different hour should miss cache
    # 1234571490 hashes to different hour (342936)
    result5 = await cached_fetch_user_data("abc123", 1234571490, True)
    assert result5["call_count"] == 3  # Should miss cache
    assert result5["user_id"] == "abc123"
    assert result5["timestamp"] == 1234571490


# Simple cached function without custom hashers
@async_cached(cache=injected("test_cache_simple"))
@instance
async def simple_cached_fetch():
    """Factory that creates a simple cached fetch function"""
    call_count = 0

    async def _fetch(user_id: str, value: int):
        nonlocal call_count
        call_count += 1
        return {"user_id": user_id, "value": value, "call_count": call_count}

    return _fetch


# Test design without custom hashers
test_design_without_hashers = design(
    test_cache_simple={}, simple_cached_fetch=simple_cached_fetch
)


@injected_pytest(test_design_without_hashers)
async def test_async_cached_without_key_hashers(simple_cached_fetch):
    """
    Control test: Verify normal caching behavior without custom key_hashers
    """
    # simple_cached_fetch is the cached interface function

    # Different parameters should always miss cache
    result1 = await simple_cached_fetch("user123", 100)
    assert result1["call_count"] == 1

    result2 = await simple_cached_fetch("user456", 100)
    assert result2["call_count"] == 2  # Different user_id, cache miss

    result3 = await simple_cached_fetch("user123", 100)
    assert result3["call_count"] == 1  # Same parameters, cache hit
    assert result3 == result1  # Should return the same cached object


if __name__ == "__main__":
    # For manual testing/debugging
    print("Running tests...")
    import asyncio

    async def run_tests():
        print("\nTesting with key_hashers...")
        # Manual test would need to set up resolver properly
        print("Please run with pytest")

    asyncio.run(run_tests())
