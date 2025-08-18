"""Real tests for decoration.py module that actually execute the code."""

import pytest
from unittest.mock import patch
from returns.maybe import Nothing, Some

from pinjected.decoration import update_if_registered
from pinjected import Injected
from pinjected.di.injected import PartialInjectedFunction
from pinjected.di.partially_injected import Partial
from pinjected.v2.binds import BindInjected
from pinjected.v2.keys import StrBindKey
from pinjected.di.metadata.bind_metadata import BindMetadata


def dummy_function(x, y):
    """A dummy function for testing."""
    return x + y


def updated_function(x, y):
    """An updated function for testing."""
    return x * y


class TestUpdateIfRegisteredReal:
    """Test update_if_registered function with real execution."""

    def test_with_partial_instance_no_binding_key(self):
        """Test update_if_registered with Partial instance and no binding_key."""
        # Create a real Partial instance - pass the raw function, not Injected
        partial = Partial(dummy_function, {})

        # Create updated function
        updated = Injected.bind(updated_function)

        # Mock IMPLICIT_BINDINGS to verify registration
        with patch(
            "pinjected.di.implicit_globals.IMPLICIT_BINDINGS", {}
        ) as mock_bindings:
            # Call the function
            result = update_if_registered(partial, updated)

            # Verify registration happened
            key = StrBindKey("dummy_function")
            assert key in mock_bindings
            assert isinstance(mock_bindings[key], BindInjected)

            # Check the result is the proxy
            assert result == updated.proxy

    def test_with_partial_instance_with_binding_key(self):
        """Test update_if_registered with Partial instance and binding_key."""
        # Create a real Partial instance
        partial = Partial(dummy_function, {})

        # Create updated function
        updated = Injected.bind(updated_function)

        # Mock IMPLICIT_BINDINGS
        with patch(
            "pinjected.di.implicit_globals.IMPLICIT_BINDINGS", {}
        ) as mock_bindings:
            # Call with custom binding key
            result = update_if_registered(partial, updated, binding_key="custom_key")

            # Verify registration with custom key
            key = StrBindKey("custom_key")
            assert key in mock_bindings
            assert isinstance(mock_bindings[key], BindInjected)

            # Check the result
            assert result == updated.proxy

    def test_with_partial_instance_with_metadata(self):
        """Test update_if_registered with metadata."""
        # Create a real Partial instance
        partial = Partial(dummy_function, {})

        # Create updated function
        updated = Injected.bind(updated_function)

        # Create metadata
        metadata = BindMetadata(code_location=Nothing, protocol=None)

        # Mock IMPLICIT_BINDINGS
        with patch(
            "pinjected.di.implicit_globals.IMPLICIT_BINDINGS", {}
        ) as mock_bindings:
            # Call with metadata
            update_if_registered(partial, updated, meta=Some(metadata))

            # Verify registration
            key = StrBindKey("dummy_function")
            assert key in mock_bindings
            bind_injected = mock_bindings[key]
            assert isinstance(bind_injected, BindInjected)
            # Check metadata was passed
            assert bind_injected._metadata == Some(metadata)

    def test_with_non_partial_instance(self):
        """Test update_if_registered with non-Partial instance."""
        # Create a regular Injected function (not Partial)
        func = Injected.bind(dummy_function)
        updated = Injected.bind(updated_function)

        # Call the function
        result = update_if_registered(func, updated)

        # Should return PartialInjectedFunction
        assert isinstance(result, PartialInjectedFunction)

    def test_isinstance_check_works(self):
        """Test that isinstance check properly identifies Partial instances."""
        # Create instances
        partial = Partial(dummy_function, {})
        non_partial = Injected.bind(dummy_function)

        # Test isinstance
        assert isinstance(partial, Partial)
        assert not isinstance(non_partial, Partial)

    def test_empty_metadata_as_nothing(self):
        """Test with empty metadata (Nothing)."""
        # Create a real Partial instance
        partial = Partial(dummy_function, {})

        # Create updated function
        updated = Injected.bind(updated_function)

        # Mock IMPLICIT_BINDINGS
        with patch(
            "pinjected.di.implicit_globals.IMPLICIT_BINDINGS", {}
        ) as mock_bindings:
            # Call with Nothing metadata (default)
            update_if_registered(partial, updated, meta=Nothing)

            # Verify registration
            key = StrBindKey("dummy_function")
            assert key in mock_bindings
            bind_injected = mock_bindings[key]
            # Metadata should be Nothing
            assert bind_injected._metadata == Nothing


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
