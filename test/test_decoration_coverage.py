"""Simple tests for decoration.py module."""

import pytest
from unittest.mock import Mock, patch
from returns.maybe import Nothing, Some

from pinjected.decoration import update_if_registered
from pinjected import Injected
from pinjected.di.partially_injected import Partial
from pinjected.di.injected import PartialInjectedFunction
from pinjected.di.metadata.bind_metadata import BindMetadata
from pinjected.v2.binds import BindInjected
from pinjected.v2.keys import StrBindKey


class TestUpdateIfRegistered:
    """Test the update_if_registered function."""

    def test_update_if_registered_with_partial(self):
        """Test update_if_registered with Partial object."""
        # Create mock functions
        mock_func = Mock()
        mock_func.__name__ = "test_func"

        mock_updated = Mock(spec=Injected)
        mock_updated.proxy = Mock()

        # Create a Partial object
        partial = Mock(spec=Partial)
        partial.src_function = mock_func

        # Patch IMPLICIT_BINDINGS
        with patch(
            "pinjected.di.implicit_globals.IMPLICIT_BINDINGS", {}
        ) as mock_bindings:
            result = update_if_registered(partial, mock_updated)

            # Should return the proxy
            assert result == mock_updated.proxy

            # Should update IMPLICIT_BINDINGS
            key = StrBindKey("test_func")
            assert key in mock_bindings
            assert isinstance(mock_bindings[key], BindInjected)

    def test_update_if_registered_with_binding_key(self):
        """Test update_if_registered with custom binding key."""
        mock_func = Mock()
        mock_func.__name__ = "test_func"

        mock_updated = Mock(spec=Injected)
        mock_updated.proxy = Mock()

        partial = Mock(spec=Partial)
        partial.src_function = mock_func

        with patch(
            "pinjected.di.implicit_globals.IMPLICIT_BINDINGS", {}
        ) as mock_bindings:
            update_if_registered(partial, mock_updated, binding_key="custom_key")

            # Should use custom key
            key = StrBindKey("custom_key")
            assert key in mock_bindings

    def test_update_if_registered_with_metadata(self):
        """Test update_if_registered with metadata."""
        mock_func = Mock()
        mock_func.__name__ = "test_func"

        mock_updated = Mock(spec=Injected)
        mock_updated.proxy = Mock()

        partial = Mock(spec=Partial)
        partial.src_function = mock_func

        # Create metadata
        metadata = Mock(spec=BindMetadata)

        with patch(
            "pinjected.di.implicit_globals.IMPLICIT_BINDINGS", {}
        ) as mock_bindings:
            update_if_registered(partial, mock_updated, meta=Some(metadata))

            # Should include metadata in binding
            key = StrBindKey("test_func")
            binding = mock_bindings[key]
            assert binding._metadata == Some(metadata)

    def test_update_if_registered_with_non_partial(self):
        """Test update_if_registered with non-Partial object."""
        mock_func = Mock()
        mock_updated = Mock(spec=Injected)

        # Test with non-Partial object
        result = update_if_registered(mock_func, mock_updated)

        # Should return PartialInjectedFunction
        assert isinstance(result, PartialInjectedFunction)

    def test_update_if_registered_nothing_metadata(self):
        """Test update_if_registered with Nothing as metadata."""
        mock_func = Mock()
        mock_func.__name__ = "test_func"

        mock_updated = Mock(spec=Injected)
        mock_updated.proxy = Mock()

        partial = Mock(spec=Partial)
        partial.src_function = mock_func

        with patch(
            "pinjected.di.implicit_globals.IMPLICIT_BINDINGS", {}
        ) as mock_bindings:
            update_if_registered(partial, mock_updated, meta=Nothing)

            # Should work with Nothing metadata
            key = StrBindKey("test_func")
            assert key in mock_bindings

    def test_update_if_registered_type_checking(self):
        """Test that isinstance is used for Partial checking."""
        # Create an actual instance of Partial (not just a mock)
        mock_src = Mock()
        mock_src.__name__ = "test"

        # Create a mock that passes isinstance check for Partial
        partial = Mock(spec=Partial)
        partial.__class__ = Partial
        partial.src_function = mock_src

        mock_updated = Mock(spec=Injected)
        mock_updated.proxy = "proxy_result"

        with patch("pinjected.di.implicit_globals.IMPLICIT_BINDINGS", {}):
            result = update_if_registered(partial, mock_updated)

            # Should return proxy
            assert result == "proxy_result"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
