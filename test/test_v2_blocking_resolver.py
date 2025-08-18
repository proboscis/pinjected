"""Tests for v2/blocking_resolver.py module."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from dataclasses import is_dataclass

from pinjected.v2.blocking_resolver import Resolver
from pinjected.v2.async_resolver import AsyncResolver


def test_resolver_is_dataclass():
    """Test that Resolver is a dataclass."""
    assert is_dataclass(Resolver)


def test_resolver_init():
    """Test Resolver initialization."""
    mock_async_resolver = Mock(spec=AsyncResolver)
    resolver = Resolver(resolver=mock_async_resolver)

    assert resolver.resolver is mock_async_resolver


@patch("asyncio.run")
def test_provide(mock_asyncio_run):
    """Test provide method."""
    # Set up mocks
    mock_async_resolver = Mock(spec=AsyncResolver)
    mock_async_resolver.provide = AsyncMock(return_value="result")
    mock_asyncio_run.return_value = "result"

    resolver = Resolver(resolver=mock_async_resolver)

    # Test provide
    target = "some_target"
    result = resolver.provide(target)

    # Verify asyncio.run was called with the coroutine
    mock_asyncio_run.assert_called_once()
    # Verify the async resolver's provide was called
    mock_async_resolver.provide.assert_called_once_with(target)
    assert result == "result"


def test_child_session():
    """Test child_session method."""
    # Set up mocks
    mock_async_resolver = Mock(spec=AsyncResolver)
    mock_child_async_resolver = Mock(spec=AsyncResolver)
    mock_async_resolver.child_session.return_value = mock_child_async_resolver

    resolver = Resolver(resolver=mock_async_resolver)

    # Test child_session
    overrides = {"key": "value"}
    child = resolver.child_session(overrides)

    # Verify child_session was called on async resolver
    mock_async_resolver.child_session.assert_called_once_with(overrides)
    # Verify returned child is a Resolver with the child async resolver
    assert isinstance(child, Resolver)
    assert child.resolver is mock_child_async_resolver


def test_to_async():
    """Test to_async method."""
    mock_async_resolver = Mock(spec=AsyncResolver)
    resolver = Resolver(resolver=mock_async_resolver)

    # Test to_async
    result = resolver.to_async()

    # Should return the async resolver
    assert result is mock_async_resolver


@patch("asyncio.run")
def test_getitem(mock_asyncio_run):
    """Test __getitem__ method."""
    # Set up mocks
    mock_async_resolver = Mock(spec=AsyncResolver)
    mock_async_resolver.provide = AsyncMock(return_value="result")
    mock_asyncio_run.return_value = "result"

    resolver = Resolver(resolver=mock_async_resolver)

    # Test __getitem__
    result = resolver["some_key"]

    # Verify it calls provide
    mock_asyncio_run.assert_called_once()
    mock_async_resolver.provide.assert_called_once_with("some_key")
    assert result == "result"


@pytest.mark.asyncio
async def test_provide_integration():
    """Test provide with actual async execution."""
    # Create a mock async resolver with real async behavior
    mock_async_resolver = Mock(spec=AsyncResolver)

    async def mock_provide(target):
        await asyncio.sleep(0.001)  # Simulate async work
        return f"provided: {target}"

    mock_async_resolver.provide = mock_provide

    # Create resolver and test in a new event loop
    Resolver(resolver=mock_async_resolver)

    # Run in a subprocess to avoid event loop conflicts
    import subprocess
    import sys

    code = """
import asyncio
from unittest.mock import Mock
from pinjected.v2.blocking_resolver import Resolver
from pinjected.v2.async_resolver import AsyncResolver

mock_async_resolver = Mock(spec=AsyncResolver)

async def mock_provide(target):
    await asyncio.sleep(0.001)
    return f"provided: {target}"

mock_async_resolver.provide = mock_provide
resolver = Resolver(resolver=mock_async_resolver)
result = resolver.provide("test_target")
print(result)
"""

    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True
    )
    assert result.stdout.strip() == "provided: test_target"


def test_resolver_with_design_type_hint():
    """Test that child_session accepts Design type hint."""
    # This is just a type hint test, no runtime behavior
    mock_async_resolver = Mock(spec=AsyncResolver)
    resolver = Resolver(resolver=mock_async_resolver)

    # Should accept any dict-like object as "Design"
    resolver.child_session({})
    resolver.child_session({"key": "value"})

    # Verify the async resolver received the overrides
    assert mock_async_resolver.child_session.call_count == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
