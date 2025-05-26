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


# Test for unpicklable parameters with custom key_hashers
class UnpicklableObject:
    """A class that cannot be pickled"""
    def __init__(self, value):
        self.value = value
        # Make it unpicklable by adding a lambda
        self.unpicklable_attr = lambda x: x * 2
    
    def get_value(self):
        return self.value


# Custom hasher that handles unpicklable objects
def hash_unpicklable_obj(obj: UnpicklableObject) -> str:
    """Hash unpicklable object by using its value attribute"""
    return f"obj_{obj.value}"


# Cached function that accepts unpicklable parameters
@async_cached(
    cache=injected("test_cache_unpicklable"),
    key_hashers=injected("test_key_hashers_unpicklable")
)
@instance
async def cached_process_unpicklable():
    """Factory that creates a function processing unpicklable objects"""
    call_count = 0
    
    async def _process(obj: UnpicklableObject, multiplier: int = 1):
        nonlocal call_count
        call_count += 1
        # Simulate some processing
        result = obj.get_value() * multiplier
        return {
            "result": result,
            "call_count": call_count,
            "obj_value": obj.value
        }
    
    return _process


# Test design for unpicklable parameters
test_design_unpicklable = design(
    test_cache_unpicklable={},
    test_key_hashers_unpicklable={
        "obj": hash_unpicklable_obj,
        # For other complex types, we could add more hashers
    },
    cached_process_unpicklable=cached_process_unpicklable
)


@injected_pytest(test_design_unpicklable)
async def test_async_cached_with_unpicklable_parameters(cached_process_unpicklable):
    """
    Test that verifies caching works with unpicklable parameters when using custom key_hashers.
    
    This is important because by default, cache keys are created by pickling the arguments,
    which would fail for unpicklable objects. Custom key_hashers allow us to bypass this.
    """
    # Create unpicklable objects
    obj1 = UnpicklableObject(value=42)
    obj2 = UnpicklableObject(value=42)  # Same value as obj1
    obj3 = UnpicklableObject(value=99)  # Different value
    
    # First call with obj1
    result1 = await cached_process_unpicklable(obj1, 2)
    assert result1["result"] == 84  # 42 * 2
    assert result1["call_count"] == 1
    
    # Call with obj2 (different instance but same value) - should hit cache
    result2 = await cached_process_unpicklable(obj2, 2)
    assert result2["result"] == 84
    assert result2["call_count"] == 1  # Cache hit!
    assert result2 == result1  # Should return the exact same cached result
    
    # Call with obj3 (different value) - should miss cache
    result3 = await cached_process_unpicklable(obj3, 2)
    assert result3["result"] == 198  # 99 * 2
    assert result3["call_count"] == 2  # Cache miss
    
    # Verify that without the key_hasher, this would fail
    # Let's also test that the hasher is actually being used
    # by checking with the same object value but different multiplier
    result4 = await cached_process_unpicklable(obj1, 3)  # Different multiplier
    assert result4["result"] == 126  # 42 * 3
    assert result4["call_count"] == 3  # Cache miss due to different multiplier


# Test with multiple unpicklable parameter types
def hash_file_handle(f) -> str:
    """Hash file handle by its name"""
    return f"file_{getattr(f, 'name', 'unknown')}"


def hash_thread_lock(lock) -> str:
    """Hash thread lock by returning a constant"""
    return "thread_lock"  # All locks hash to the same value


@async_cached(
    cache=injected("test_cache_complex"),
    key_hashers=injected("test_key_hashers_complex")
)
@instance
async def cached_complex_unpicklable():
    """Factory for a function with multiple unpicklable parameter types"""
    call_count = 0
    
    async def _process(obj: UnpicklableObject, file_handle=None, lock=None, data: str = ""):
        nonlocal call_count
        call_count += 1
        return {
            "obj_value": obj.value,
            "has_file": file_handle is not None,
            "has_lock": lock is not None,
            "data": data,
            "call_count": call_count
        }
    
    return _process


import threading
from io import StringIO


test_design_complex = design(
    test_cache_complex={},
    test_key_hashers_complex={
        "obj": hash_unpicklable_obj,
        "file_handle": hash_file_handle,
        "lock": hash_thread_lock,
    },
    cached_complex_unpicklable=cached_complex_unpicklable
)


@injected_pytest(test_design_complex)
async def test_async_cached_with_multiple_unpicklable_types(cached_complex_unpicklable):
    """
    Test caching with multiple types of unpicklable parameters.
    
    This demonstrates how key_hashers can handle various unpicklable types
    like file handles, thread locks, and custom objects.
    """
    obj = UnpicklableObject(value=100)
    file1 = StringIO("test data")
    file1.name = "test.txt"
    file2 = StringIO("different data")
    file2.name = "test.txt"  # Same name as file1
    lock1 = threading.Lock()
    lock2 = threading.Lock()  # Different lock instance
    
    # First call
    result1 = await cached_complex_unpicklable(obj, file1, lock1, "hello")
    assert result1["call_count"] == 1
    
    # Call with different file object but same name - should hit cache
    result2 = await cached_complex_unpicklable(obj, file2, lock1, "hello")
    assert result2["call_count"] == 1  # Cache hit due to hash_file_handle
    
    # Call with different lock instance - should still hit cache
    result3 = await cached_complex_unpicklable(obj, file1, lock2, "hello")
    assert result3["call_count"] == 1  # Cache hit due to hash_thread_lock
    
    # Call with different data - should miss cache
    result4 = await cached_complex_unpicklable(obj, file1, lock1, "world")
    assert result4["call_count"] == 2  # Cache miss due to different data
