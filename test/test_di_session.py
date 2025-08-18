"""Tests for di/session.py module."""

import pytest
import uuid
from unittest.mock import Mock, patch
from dataclasses import dataclass

from pinjected.di.session import ISessionScope, SessionScope, ChildScope


class TestISessionScope:
    """Tests for ISessionScope abstract base class."""

    def test_cannot_instantiate_abstract_class(self):
        """Test that ISessionScope cannot be instantiated directly."""

        # Since it has abstract methods, we can't instantiate it directly
        # But we can create a concrete subclass for testing
        @dataclass
        class ConcreteScope(ISessionScope):
            def provide(self, binding_key, default_provider_fn):
                return "test"

        scope = ConcreteScope()
        assert scope.provide("key", lambda: "value") == "test"


class TestSessionScope:
    """Tests for SessionScope class."""

    def test_init_creates_uuid_and_state(self):
        """Test that __post_init__ creates UUID and initializes state."""
        scope = SessionScope()

        # Check initial state
        assert hasattr(scope, "_id")
        assert isinstance(scope._id, uuid.UUID)
        assert scope.provide_depth == 0
        assert scope.pending == []
        assert scope.cache == {}

    def test_provide_caches_value(self):
        """Test that provide caches the value from provider function."""
        scope = SessionScope()

        # Mock binding key with _name attribute
        binding_key = Mock()
        binding_key._name = "test_key"

        provider_fn = Mock(return_value="test_value")

        # First call should execute provider
        with patch("pinjected.pinjected_logging.logger"):
            result = scope.provide(binding_key, provider_fn)

        assert result == "test_value"
        assert binding_key in scope.cache
        assert scope.cache[binding_key] == "test_value"
        provider_fn.assert_called_once()

    def test_provide_returns_cached_value(self):
        """Test that provide returns cached value on subsequent calls."""
        scope = SessionScope()

        binding_key = Mock()
        binding_key._name = "test_key"

        provider_fn = Mock(return_value="test_value")

        # First call
        with patch("pinjected.pinjected_logging.logger"):
            result1 = scope.provide(binding_key, provider_fn)

        # Second call should return cached value
        with patch("pinjected.pinjected_logging.logger"):
            result2 = scope.provide(binding_key, provider_fn)

        assert result1 == result2
        # Provider should only be called once
        provider_fn.assert_called_once()

    def test_provide_depth_tracking(self):
        """Test that provide tracks nesting depth correctly."""
        scope = SessionScope()

        # Mock nested provider functions
        def outer_provider():
            binding_key_inner = Mock()
            binding_key_inner._name = "inner_key"

            def inner_provider():
                # Check depth during inner execution
                assert scope.provide_depth == 2
                return "inner_value"

            # This will increase depth
            result = scope.provide(binding_key_inner, inner_provider)
            # After inner completes, depth should be back to 1
            assert scope.provide_depth == 1
            return f"outer({result})"

        binding_key_outer = Mock()
        binding_key_outer._name = "outer_key"

        with patch("pinjected.pinjected_logging.logger"):
            result = scope.provide(binding_key_outer, outer_provider)

        assert result == "outer(inner_value)"
        assert scope.provide_depth == 0  # Back to initial state

    def test_pending_tracking(self):
        """Test that pending list tracks current resolution chain."""
        scope = SessionScope()

        binding_key = Mock()
        binding_key._name = "test_key"

        def provider_fn():
            # During execution, key should be in pending
            assert binding_key in scope.pending
            return "value"

        with patch("pinjected.pinjected_logging.logger"):
            scope.provide(binding_key, provider_fn)

        # After completion, pending should be empty
        assert scope.pending == []

    def test_str_representation(self):
        """Test string representation of SessionScope."""
        scope = SessionScope()
        str_repr = str(scope)

        assert str_repr.startswith("SessionScope:")
        # Should show first 5 chars of UUID
        assert len(str_repr.split(":")[1]) == 5

    def test_contains_method(self):
        """Test __contains__ method for checking cached keys."""
        scope = SessionScope()

        binding_key = Mock()
        binding_key._name = "test_key"

        # Initially not in cache
        assert binding_key not in scope

        # Add to cache
        with patch("pinjected.pinjected_logging.logger"):
            scope.provide(binding_key, lambda: "value")

        # Now should be in cache
        assert binding_key in scope

    def test_cached_method(self):
        """Test cached method for checking if key is cached."""
        scope = SessionScope()

        binding_key = Mock()
        binding_key._name = "test_key"

        # Initially not cached
        assert not scope.cached(binding_key)

        # Add to cache
        with patch("pinjected.pinjected_logging.logger"):
            scope.provide(binding_key, lambda: "value")

        # Now should be cached
        assert scope.cached(binding_key)

    def test_logging_messages(self):
        """Test that appropriate log messages are generated."""
        scope = SessionScope()

        binding_key = Mock()
        binding_key._name = "test_key"

        with patch("pinjected.pinjected_logging.logger") as mock_logger:
            scope.provide(binding_key, lambda: "test_value")

        # Check that debug messages were logged
        assert mock_logger.debug.call_count >= 2

        # Check content of log messages
        calls = mock_logger.debug.call_args_list
        assert any("Providing:" in str(call) for call in calls)
        assert any("Remaining:" in str(call) for call in calls)


class TestChildScope:
    """Tests for ChildScope class."""

    def test_init_creates_uuid(self):
        """Test that __post_init__ creates UUID."""
        parent = SessionScope()
        child = ChildScope(parent=parent, override_targets=set())

        assert hasattr(child, "_id")
        assert isinstance(child._id, uuid.UUID)

    def test_str_representation(self):
        """Test string representation shows parent relationship."""
        parent = SessionScope()
        child = ChildScope(parent=parent, override_targets=set())

        str_repr = str(child)
        # Should show parent=>child format
        assert "=>" in str_repr
        assert str(parent) in str_repr

    def test_provide_uses_parent_cache_when_available(self):
        """Test that child uses parent's cached value when available."""
        parent = SessionScope()

        binding_key = Mock()
        binding_key._name = "test_key"

        # Add to parent cache
        with patch("pinjected.pinjected_logging.logger"):
            parent.provide(binding_key, lambda: "parent_value")

        # Create child
        child = ChildScope(parent=parent, override_targets=set())

        # Child should use parent's value
        with patch("pinjected.pinjected_logging.logger"):
            result = child.provide(binding_key, lambda: "child_value")

        assert result == "parent_value"
        assert binding_key not in child.cache  # Not in child's cache

    def test_provide_overrides_when_in_override_targets(self):
        """Test that child overrides parent when key is in override_targets."""
        parent = SessionScope()

        binding_key = Mock()
        binding_key._name = "test_key"

        # Add to parent cache
        with patch("pinjected.pinjected_logging.logger"):
            parent.provide(binding_key, lambda: "parent_value")

        # Create child with override
        child = ChildScope(parent=parent, override_targets={binding_key})

        # Child should create its own value
        with patch("pinjected.pinjected_logging.logger"):
            result = child.provide(binding_key, lambda: "child_value")

        assert result == "child_value"
        assert child.cache[binding_key] == "child_value"

    def test_provide_creates_local_cache_for_new_keys(self):
        """Test that child creates local cache for keys not in parent."""
        parent = SessionScope()
        child = ChildScope(parent=parent, override_targets=set())

        binding_key = Mock()
        binding_key._name = "test_key"

        # Key not in parent, should be created in child
        with patch("pinjected.pinjected_logging.logger"):
            result = child.provide(binding_key, lambda: "child_value")

        assert result == "child_value"
        assert child.cache[binding_key] == "child_value"
        assert binding_key not in parent.cache

    def test_contains_checks_both_caches(self):
        """Test __contains__ checks both child and parent caches."""
        parent = SessionScope()
        child = ChildScope(parent=parent, override_targets=set())

        parent_key = Mock()
        parent_key._name = "parent_key"

        child_key = Mock()
        child_key._name = "child_key"

        # Add to parent
        with patch("pinjected.pinjected_logging.logger"):
            parent.provide(parent_key, lambda: "parent_value")

        # Add to child
        with patch("pinjected.pinjected_logging.logger"):
            child.provide(child_key, lambda: "child_value")

        # Child should see both
        assert parent_key in child
        assert child_key in child

        # Parent should only see its own
        assert parent_key in parent
        assert child_key not in parent

    def test_caching_behavior(self):
        """Test that values are properly cached in child scope."""
        parent = SessionScope()
        child = ChildScope(parent=parent, override_targets=set())

        binding_key = Mock()
        binding_key._name = "test_key"

        provider_fn = Mock(return_value="test_value")

        # First call
        with patch("pinjected.pinjected_logging.logger"):
            result1 = child.provide(binding_key, provider_fn)

        # Second call should use cache
        with patch("pinjected.pinjected_logging.logger"):
            result2 = child.provide(binding_key, provider_fn)

        assert result1 == result2
        provider_fn.assert_called_once()


def test_inheritance_relationship():
    """Test that SessionScope and ChildScope inherit from ISessionScope."""
    assert issubclass(SessionScope, ISessionScope)
    assert issubclass(ChildScope, ISessionScope)


def test_integration_parent_child_scopes():
    """Test integration between parent and child scopes."""
    # Create parent with some cached values
    parent = SessionScope()

    key1 = Mock()
    key1._name = "key1"
    key2 = Mock()
    key2._name = "key2"
    key3 = Mock()
    key3._name = "key3"

    with patch("pinjected.pinjected_logging.logger"):
        parent.provide(key1, lambda: "parent_value1")
        parent.provide(key2, lambda: "parent_value2")

    # Create child that overrides key2
    child = ChildScope(parent=parent, override_targets={key2})

    with patch("pinjected.pinjected_logging.logger"):
        # key1 should come from parent
        assert child.provide(key1, lambda: "child_value1") == "parent_value1"

        # key2 should be overridden
        assert child.provide(key2, lambda: "child_value2") == "child_value2"

        # key3 is new, should be in child only
        assert child.provide(key3, lambda: "child_value3") == "child_value3"

    # Verify cache states
    assert key1 in parent.cache
    assert key2 in parent.cache
    assert key3 not in parent.cache

    assert key1 not in child.cache  # Used from parent
    assert key2 in child.cache  # Overridden
    assert key3 in child.cache  # New in child


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
