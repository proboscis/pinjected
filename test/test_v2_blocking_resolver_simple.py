"""Simple tests for v2/blocking_resolver.py module."""

import pytest
from unittest.mock import patch, Mock, AsyncMock
from dataclasses import is_dataclass
import asyncio

from pinjected.v2.blocking_resolver import Resolver


class TestBlockingResolver:
    """Test the Resolver (blocking) class."""

    def test_resolver_is_dataclass(self):
        """Test that Resolver is a dataclass."""
        assert is_dataclass(Resolver)

    def test_resolver_init(self):
        """Test Resolver initialization."""
        mock_async_resolver = Mock()
        resolver = Resolver(resolver=mock_async_resolver)

        assert resolver.resolver is mock_async_resolver

    @patch("pinjected.v2.blocking_resolver.asyncio.run")
    def test_provide(self, mock_asyncio_run):
        """Test provide method."""
        # Setup
        mock_async_resolver = Mock()
        mock_async_provide = AsyncMock(return_value="provided_value")
        mock_async_resolver.provide = mock_async_provide
        mock_asyncio_run.return_value = "provided_value"

        resolver = Resolver(resolver=mock_async_resolver)

        # Call provide
        result = resolver.provide("test_key")

        # Verify
        assert result == "provided_value"
        mock_asyncio_run.assert_called_once()

        # Check that the coroutine was created
        coro = mock_asyncio_run.call_args[0][0]
        assert asyncio.iscoroutine(coro)
        coro.close()  # Clean up the coroutine

    def test_child_session(self):
        """Test child_session method."""
        # Setup
        mock_async_resolver = Mock()
        mock_child_async_resolver = Mock()
        mock_async_resolver.child_session.return_value = mock_child_async_resolver

        resolver = Resolver(resolver=mock_async_resolver)

        # Call child_session
        design_overrides = {"key": "value"}
        child = resolver.child_session(design_overrides)

        # Verify
        assert isinstance(child, Resolver)
        assert child.resolver is mock_child_async_resolver
        mock_async_resolver.child_session.assert_called_once_with(design_overrides)

    def test_to_async(self):
        """Test to_async method."""
        mock_async_resolver = Mock()
        resolver = Resolver(resolver=mock_async_resolver)

        result = resolver.to_async()

        assert result is mock_async_resolver

    @patch("pinjected.v2.blocking_resolver.asyncio.run")
    def test_getitem(self, mock_asyncio_run):
        """Test __getitem__ method."""
        # Setup
        mock_async_resolver = Mock()
        mock_async_provide = AsyncMock(return_value="item_value")
        mock_async_resolver.provide = mock_async_provide
        mock_asyncio_run.return_value = "item_value"

        resolver = Resolver(resolver=mock_async_resolver)

        # Call __getitem__
        result = resolver["test_key"]

        # Verify
        assert result == "item_value"
        mock_asyncio_run.assert_called_once()

    @patch("pinjected.v2.blocking_resolver.asyncio.run")
    def test_find_provision_errors(self, mock_asyncio_run):
        """Test find_provision_errors method."""
        # Setup
        mock_async_resolver = Mock()
        mock_async_method = AsyncMock(return_value=["error1", "error2"])
        mock_async_resolver.a_find_provision_errors = mock_async_method
        mock_asyncio_run.return_value = ["error1", "error2"]

        resolver = Resolver(resolver=mock_async_resolver)

        # Call find_provision_errors
        result = resolver.find_provision_errors("test_key")

        # Verify
        assert result == ["error1", "error2"]
        mock_asyncio_run.assert_called_once()

        # Check that the coroutine was created
        coro = mock_asyncio_run.call_args[0][0]
        assert asyncio.iscoroutine(coro)
        coro.close()  # Clean up the coroutine

    @patch("pinjected.v2.blocking_resolver.asyncio.run")
    def test_check_resolution(self, mock_asyncio_run):
        """Test check_resolution method."""
        # Setup
        mock_async_resolver = Mock()
        mock_async_method = AsyncMock(return_value=True)
        mock_async_resolver.a_check_resolution = mock_async_method
        mock_asyncio_run.return_value = True

        resolver = Resolver(resolver=mock_async_resolver)

        # Call check_resolution
        result = resolver.check_resolution("test_key")

        # Verify
        assert result is True
        mock_asyncio_run.assert_called_once()

        # Check that the coroutine was created
        coro = mock_asyncio_run.call_args[0][0]
        assert asyncio.iscoroutine(coro)
        coro.close()  # Clean up the coroutine

    def test_type_checking_imports(self):
        """Test TYPE_CHECKING imports are handled correctly."""
        # This test ensures the module can be imported without issues
        from pinjected.v2 import blocking_resolver

        # Check that Resolver is available
        assert hasattr(blocking_resolver, "Resolver")

        # Check imports
        assert hasattr(blocking_resolver, "AsyncResolver")
        assert hasattr(blocking_resolver, "Providable")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
