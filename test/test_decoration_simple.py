"""Simple tests for decoration.py module."""

import pytest
from unittest.mock import patch
from returns.maybe import Nothing, Some

from pinjected import Injected
from pinjected.decoration import update_if_registered
from pinjected.di.injected import PartialInjectedFunction
from pinjected.di.partially_injected import Partial
from pinjected.di.metadata.bind_metadata import BindMetadata
from pinjected.v2.binds import BindInjected
from pinjected.v2.keys import StrBindKey


class TestUpdateIfRegistered:
    """Test the update_if_registered function."""

    def test_update_if_registered_with_partial(self):
        """Test update_if_registered with Partial instance."""

        # Create mock functions
        def original_func():
            return "original"

        def updated_func():
            return "updated"

        # Create a Partial instance
        partial = Partial(src_function=original_func, injection_targets={})

        # Create injected versions
        injected_updated = Injected.pure(updated_func)

        # Mock IMPLICIT_BINDINGS
        with patch(
            "pinjected.di.implicit_globals.IMPLICIT_BINDINGS", {}
        ) as mock_bindings:
            # Call update_if_registered
            result = update_if_registered(partial, injected_updated)

            # Check that IMPLICIT_BINDINGS was updated
            expected_key = StrBindKey("original_func")
            assert expected_key in mock_bindings
            binding = mock_bindings[expected_key]
            assert isinstance(binding, BindInjected)
            assert binding.src == injected_updated

            # Result should be updated.proxy
            assert result == injected_updated.proxy

    def test_update_if_registered_with_partial_and_binding_key(self):
        """Test update_if_registered with Partial and custom binding key."""

        # Create mock functions
        def original_func():
            return "original"

        def updated_func():
            return "updated"

        # Create a Partial instance
        partial = Partial(src_function=original_func, injection_targets={})

        # Create injected versions
        injected_updated = Injected.pure(updated_func)

        # Mock IMPLICIT_BINDINGS
        with patch(
            "pinjected.di.implicit_globals.IMPLICIT_BINDINGS", {}
        ) as mock_bindings:
            # Call with custom binding key
            result = update_if_registered(
                partial, injected_updated, binding_key="custom_key"
            )

            # Check that IMPLICIT_BINDINGS was updated with custom key
            expected_key = StrBindKey("custom_key")
            assert expected_key in mock_bindings
            binding = mock_bindings[expected_key]
            assert isinstance(binding, BindInjected)
            assert binding.src == injected_updated

            # Result should be updated.proxy
            assert result == injected_updated.proxy

    def test_update_if_registered_with_partial_and_metadata(self):
        """Test update_if_registered with Partial and metadata."""

        # Create mock functions
        def original_func():
            return "original"

        def updated_func():
            return "updated"

        # Create a Partial instance
        partial = Partial(src_function=original_func, injection_targets={})

        # Create injected versions
        injected_updated = Injected.pure(updated_func)

        # Create metadata
        metadata = BindMetadata(code_location=None)

        # Mock IMPLICIT_BINDINGS
        with patch(
            "pinjected.di.implicit_globals.IMPLICIT_BINDINGS", {}
        ) as mock_bindings:
            # Call with metadata
            update_if_registered(partial, injected_updated, meta=Some(metadata))

            # Check that IMPLICIT_BINDINGS was updated
            expected_key = StrBindKey("original_func")
            assert expected_key in mock_bindings
            binding = mock_bindings[expected_key]
            assert isinstance(binding, BindInjected)
            assert binding._metadata == Some(metadata)

    def test_update_if_registered_with_non_partial(self):
        """Test update_if_registered with non-Partial injected function."""

        # Create mock function
        def some_func():
            return "result"

        # Create injected versions
        injected_func = Injected.pure(some_func)
        injected_updated = Injected.pure(lambda: "updated")

        # Call update_if_registered
        result = update_if_registered(injected_func, injected_updated)

        # Result should be a PartialInjectedFunction
        assert isinstance(result, PartialInjectedFunction)

    def test_update_if_registered_with_nothing_metadata(self):
        """Test update_if_registered with Nothing metadata (default)."""

        # Create mock functions
        def original_func():
            return "original"

        def updated_func():
            return "updated"

        # Create a Partial instance
        partial = Partial(src_function=original_func, injection_targets={})

        # Create injected versions
        injected_updated = Injected.pure(updated_func)

        # Mock IMPLICIT_BINDINGS
        with patch(
            "pinjected.di.implicit_globals.IMPLICIT_BINDINGS", {}
        ) as mock_bindings:
            # Call without metadata (default Nothing)
            update_if_registered(partial, injected_updated)

            # Check that IMPLICIT_BINDINGS was updated
            expected_key = StrBindKey("original_func")
            assert expected_key in mock_bindings
            binding = mock_bindings[expected_key]
            assert binding._metadata == Nothing

    def test_update_if_registered_pattern_matching(self):
        """Test that pattern matching works correctly."""

        # Test with different types
        class NotPartial:
            pass

        not_partial = NotPartial()
        injected_updated = Injected.pure(lambda: "test")

        # Should go to default case
        result = update_if_registered(not_partial, injected_updated)
        assert isinstance(result, PartialInjectedFunction)

    def test_partial_isinstance_check(self):
        """Test that isinstance check works for Partial."""

        def test_func():
            return "test"

        partial = Partial(src_function=test_func, injection_targets={})
        assert isinstance(partial, Partial)

        # Create injected
        injected_updated = Injected.pure(lambda: "updated")

        with patch(
            "pinjected.di.implicit_globals.IMPLICIT_BINDINGS", {}
        ) as mock_bindings:
            update_if_registered(partial, injected_updated)
            # Should have gone through the Partial branch
            assert StrBindKey("test_func") in mock_bindings


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
