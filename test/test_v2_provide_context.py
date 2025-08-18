"""Tests for v2/provide_context.py module."""

import pytest
from unittest.mock import Mock
from pinjected.v2.provide_context import ProvideContext
from pinjected.v2.keys import IBindKey, StrBindKey


def test_provide_context_creation():
    """Test ProvideContext dataclass creation."""
    mock_resolver = Mock()
    mock_key = Mock(spec=IBindKey)

    context = ProvideContext(resolver=mock_resolver, key=mock_key, parent=None)

    assert context.resolver is mock_resolver
    assert context.key is mock_key
    assert context.parent is None


def test_provide_context_with_none_key():
    """Test ProvideContext with None key."""
    mock_resolver = Mock()

    context = ProvideContext(resolver=mock_resolver, key=None, parent=None)

    assert context.key is None


def test_provide_context_invalid_key():
    """Test ProvideContext raises error for non-IBindKey key."""
    mock_resolver = Mock()

    with pytest.raises(AssertionError, match="key must be an instance of IBindKey"):
        ProvideContext(resolver=mock_resolver, key="not_a_bind_key", parent=None)


def test_provide_context_trace_single():
    """Test trace property with single context."""
    mock_resolver = Mock()
    mock_key = Mock(spec=IBindKey)

    context = ProvideContext(resolver=mock_resolver, key=mock_key, parent=None)

    assert context.trace == [context]


def test_provide_context_trace_chain():
    """Test trace property with parent chain."""
    mock_resolver = Mock()

    # Create parent context
    parent_key = Mock(spec=IBindKey)
    parent = ProvideContext(resolver=mock_resolver, key=parent_key, parent=None)

    # Create child context
    child_key = Mock(spec=IBindKey)
    child = ProvideContext(resolver=mock_resolver, key=child_key, parent=parent)

    # Create grandchild context
    grandchild_key = Mock(spec=IBindKey)
    grandchild = ProvideContext(
        resolver=mock_resolver, key=grandchild_key, parent=child
    )

    assert grandchild.trace == [parent, child, grandchild]


def test_provide_context_trace_str_single():
    """Test trace_str property with single context."""
    mock_resolver = Mock()
    mock_key = Mock(spec=IBindKey)
    mock_key.ide_hint_string.return_value = "test_key"

    context = ProvideContext(resolver=mock_resolver, key=mock_key, parent=None)

    assert context.trace_str == "test_key"


def test_provide_context_trace_str_none_key():
    """Test trace_str property with None key."""
    mock_resolver = Mock()

    context = ProvideContext(resolver=mock_resolver, key=None, parent=None)

    assert context.trace_str == "None"


def test_provide_context_trace_str_chain():
    """Test trace_str property with parent chain."""
    mock_resolver = Mock()

    # Create parent with StrBindKey
    parent_key = StrBindKey(name="parent_key")
    parent = ProvideContext(resolver=mock_resolver, key=parent_key, parent=None)

    # Create child with StrBindKey
    child_key = StrBindKey(name="child_key")
    child = ProvideContext(resolver=mock_resolver, key=child_key, parent=parent)

    # Create grandchild with None key
    grandchild = ProvideContext(resolver=mock_resolver, key=None, parent=child)

    assert grandchild.trace_str == "parent_key -> child_key -> None"


def test_provide_context_complex_trace():
    """Test complex trace with multiple levels."""
    mock_resolver = Mock()

    # Build a complex trace
    root = ProvideContext(resolver=mock_resolver, key=None, parent=None)

    level1 = ProvideContext(
        resolver=mock_resolver, key=StrBindKey(name="service"), parent=root
    )

    level2 = ProvideContext(
        resolver=mock_resolver, key=StrBindKey(name="database"), parent=level1
    )

    level3 = ProvideContext(
        resolver=mock_resolver, key=StrBindKey(name="connection"), parent=level2
    )

    # Check full trace
    assert len(level3.trace) == 4
    assert level3.trace_str == "None -> service -> database -> connection"


def test_provide_context_with_mock_bind_key():
    """Test ProvideContext with mocked IBindKey."""
    mock_resolver = Mock()
    mock_key = Mock(spec=IBindKey)
    mock_key.ide_hint_string.return_value = "mocked_key_hint"

    parent = ProvideContext(resolver=mock_resolver, key=mock_key, parent=None)

    child_key = Mock(spec=IBindKey)
    child_key.ide_hint_string.return_value = "child_hint"
    child = ProvideContext(resolver=mock_resolver, key=child_key, parent=parent)

    assert child.trace_str == "mocked_key_hint -> child_hint"

    # Verify methods were called
    mock_key.ide_hint_string.assert_called_once()
    child_key.ide_hint_string.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
