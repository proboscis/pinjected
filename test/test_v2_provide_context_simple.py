"""Simple tests for v2/provide_context.py module."""

import pytest
from unittest.mock import Mock
from dataclasses import is_dataclass

from pinjected.v2.provide_context import ProvideContext
from pinjected.v2.keys import IBindKey, StrBindKey


class TestProvideContext:
    """Test the ProvideContext dataclass."""

    def test_provide_context_is_dataclass(self):
        """Test that ProvideContext is a dataclass."""
        assert is_dataclass(ProvideContext)

    def test_provide_context_creation(self):
        """Test creating ProvideContext instance."""
        mock_resolver = Mock()
        mock_key = Mock(spec=IBindKey)

        context = ProvideContext(resolver=mock_resolver, key=mock_key, parent=None)

        assert context.resolver is mock_resolver
        assert context.key is mock_key
        assert context.parent is None

    def test_provide_context_with_none_key(self):
        """Test creating ProvideContext with None key."""
        mock_resolver = Mock()

        context = ProvideContext(resolver=mock_resolver, key=None, parent=None)

        assert context.key is None

    def test_provide_context_post_init_validation(self):
        """Test that post_init validates key type."""
        mock_resolver = Mock()

        # Should raise assertion error for non-IBindKey
        with pytest.raises(AssertionError) as exc_info:
            ProvideContext(resolver=mock_resolver, key="not_a_bind_key", parent=None)

        assert "key must be an instance of IBindKey" in str(exc_info.value)

    def test_trace_property_single_context(self):
        """Test trace property with single context."""
        mock_resolver = Mock()
        mock_key = StrBindKey(name="test")

        context = ProvideContext(resolver=mock_resolver, key=mock_key, parent=None)

        trace = context.trace
        assert len(trace) == 1
        assert trace[0] is context

    def test_trace_property_nested_contexts(self):
        """Test trace property with nested contexts."""
        mock_resolver = Mock()

        # Create parent context
        parent_key = StrBindKey(name="parent")
        parent_context = ProvideContext(
            resolver=mock_resolver, key=parent_key, parent=None
        )

        # Create child context
        child_key = StrBindKey(name="child")
        child_context = ProvideContext(
            resolver=mock_resolver, key=child_key, parent=parent_context
        )

        # Create grandchild context
        grandchild_key = StrBindKey(name="grandchild")
        grandchild_context = ProvideContext(
            resolver=mock_resolver, key=grandchild_key, parent=child_context
        )

        trace = grandchild_context.trace
        assert len(trace) == 3
        assert trace[0] is parent_context
        assert trace[1] is child_context
        assert trace[2] is grandchild_context

    def test_trace_str_property(self):
        """Test trace_str property."""
        mock_resolver = Mock()

        # Create parent context
        parent_key = StrBindKey(name="parent_service")
        parent_context = ProvideContext(
            resolver=mock_resolver, key=parent_key, parent=None
        )

        # Create child context
        child_key = StrBindKey(name="child_service")
        child_context = ProvideContext(
            resolver=mock_resolver, key=child_key, parent=parent_context
        )

        trace_str = child_context.trace_str
        assert trace_str == "parent_service -> child_service"

    def test_trace_str_with_none_key(self):
        """Test trace_str with None key in trace."""
        mock_resolver = Mock()

        # Create parent context with None key
        parent_context = ProvideContext(resolver=mock_resolver, key=None, parent=None)

        # Create child context
        child_key = StrBindKey(name="child")
        child_context = ProvideContext(
            resolver=mock_resolver, key=child_key, parent=parent_context
        )

        trace_str = child_context.trace_str
        assert trace_str == "None -> child"

    def test_trace_str_with_long_key_names(self):
        """Test trace_str with keys that have long names."""
        mock_resolver = Mock()

        # Create key with long name
        long_name = "this_is_a_very_long_service_name_exceeding_twenty_chars"
        long_key = StrBindKey(name=long_name)

        context = ProvideContext(resolver=mock_resolver, key=long_key, parent=None)

        trace_str = context.trace_str
        # Should use ide_hint_string which truncates long names
        assert len(trace_str) < len(long_name)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
