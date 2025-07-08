"""Simple tests for di/graph.py module to improve coverage."""

import pytest
from unittest.mock import Mock
from dataclasses import is_dataclass
import threading
from concurrent.futures import Future
from returns.result import Success

from pinjected.di.graph import (
    MissingDependencyException,
    OGFactoryByDesign,
    ProvideEvent,
    RichTraceLogger,
    MScope,
    MChildScope,
    OverridingScope,
    NoMappingError,
    DependencyResolver,
)
from pinjected.exceptions import DependencyResolutionFailure
from pinjected.v2.keys import StrBindKey
from returns.maybe import Nothing, Some
from pinjected.di.injected import InjectedPure


class TestMissingDependencyException:
    """Test the MissingDependencyException class."""

    def test_create_message_empty(self):
        """Test create_message with empty list."""
        message = MissingDependencyException.create_message([])

        assert isinstance(message, str)
        assert "Missing dependencies" in message

    def test_create_message_with_failures(self):
        """Test create_message with dependency failures."""
        failure1 = DependencyResolutionFailure(
            key="dep1", trace=["A", "B", "dep1"], cause=ValueError("Not found")
        )
        failure2 = DependencyResolutionFailure(
            key="dep2", trace=["X", "Y", "dep2"], cause=KeyError("Missing")
        )

        message = MissingDependencyException.create_message([failure1, failure2])

        assert "dep1" in message
        assert "dep2" in message
        assert "Missing dependencies" in message


class TestOGFactoryByDesign:
    """Test the OGFactoryByDesign class."""

    def test_og_factory_by_design_is_dataclass(self):
        """Test that OGFactoryByDesign is a dataclass."""
        assert is_dataclass(OGFactoryByDesign)

    def test_og_factory_by_design_creation(self):
        """Test creating OGFactoryByDesign instance."""
        mock_design = Mock()
        factory = OGFactoryByDesign(d=mock_design)

        assert factory.d is mock_design

    def test_create_graph(self):
        """Test create_graph method."""
        mock_design = Mock()
        mock_design.to_graph.return_value = Mock()

        factory = OGFactoryByDesign(d=mock_design)
        graph = factory.create_graph()

        mock_design.to_graph.assert_called_once()
        assert graph is mock_design.to_graph.return_value


class TestProvideEvent:
    """Test the ProvideEvent dataclass."""

    def test_provide_event_is_dataclass(self):
        """Test that ProvideEvent is a dataclass."""
        assert is_dataclass(ProvideEvent)

    def test_provide_event_creation(self):
        """Test creating ProvideEvent instance."""
        key = StrBindKey("test")
        metadata = {"info": "test"}

        event = ProvideEvent(key=key, metadata=metadata)

        assert event.key == key
        assert event.metadata == metadata


class TestRichTraceLogger:
    """Test the RichTraceLogger class."""

    def test_rich_trace_logger_is_dataclass(self):
        """Test that RichTraceLogger is a dataclass."""
        assert is_dataclass(RichTraceLogger)

    def test_rich_trace_logger_creation(self):
        """Test creating RichTraceLogger instance."""
        logger = RichTraceLogger()

        assert hasattr(logger, "graph")
        assert hasattr(logger, "trace")
        assert hasattr(logger, "result")
        assert logger.graph is None
        assert logger.trace == []
        assert logger.result is None

    def test_rich_trace_logger_with_values(self):
        """Test RichTraceLogger with custom values."""
        mock_graph = Mock()
        trace = ["A", "B", "C"]
        result = Success("value")

        logger = RichTraceLogger(graph=mock_graph, trace=trace, result=result)

        assert logger.graph is mock_graph
        assert logger.trace == trace
        assert logger.result == result


class TestMScope:
    """Test the MScope class."""

    def test_mscope_is_dataclass(self):
        """Test that MScope is a dataclass."""
        assert is_dataclass(MScope)

    def test_mscope_creation(self):
        """Test creating MScope instance."""
        values = {StrBindKey("a"): "value_a"}
        scope = MScope(values=values)

        assert scope.values == values
        assert hasattr(scope, "lock")
        assert isinstance(scope.lock, type(threading.RLock()))

    def test_mscope_get_existing(self):
        """Test get method for existing key."""
        key = StrBindKey("test")
        value = "test_value"
        scope = MScope(values={key: value})

        result = scope.get(key)
        assert result == Some(value)

    def test_mscope_get_missing(self):
        """Test get method for missing key."""
        scope = MScope(values={})
        result = scope.get(StrBindKey("missing"))

        assert result == Nothing

    def test_mscope_set(self):
        """Test set method."""
        scope = MScope(values={})
        key = StrBindKey("new")
        value = "new_value"

        scope.set(key, value)

        assert scope.values[key] == value
        assert scope.get(key) == Some(value)

    def test_mscope_set_future(self):
        """Test set_future method."""
        scope = MScope(values={})
        key = StrBindKey("future")
        future = Future()

        scope.set_future(key, future)

        assert scope.values[key] is future


class TestMChildScope:
    """Test the MChildScope class."""

    def test_mchild_scope_is_dataclass(self):
        """Test that MChildScope is a dataclass."""
        assert is_dataclass(MChildScope)

    def test_mchild_scope_creation(self):
        """Test creating MChildScope instance."""
        parent = MScope(values={StrBindKey("parent"): "parent_value"})
        scope = MChildScope(parent=parent)

        assert scope.parent is parent
        assert scope.values == {}

    def test_mchild_scope_get_from_parent(self):
        """Test get method falls back to parent."""
        parent_key = StrBindKey("parent_key")
        parent = MScope(values={parent_key: "parent_value"})
        child = MChildScope(parent=parent)

        # Should get from parent
        result = child.get(parent_key)
        assert result == Some("parent_value")

    def test_mchild_scope_get_overrides_parent(self):
        """Test child values override parent."""
        key = StrBindKey("shared")
        parent = MScope(values={key: "parent_value"})
        child = MChildScope(parent=parent, values={key: "child_value"})

        # Should get child value
        result = child.get(key)
        assert result == Some("child_value")


class TestOverridingScope:
    """Test the OverridingScope class."""

    def test_overriding_scope_is_dataclass(self):
        """Test that OverridingScope is a dataclass."""
        assert is_dataclass(OverridingScope)

    def test_overriding_scope_creation(self):
        """Test creating OverridingScope instance."""
        base = MScope(values={StrBindKey("base"): "base_value"})
        overrides = {StrBindKey("override"): "override_value"}

        scope = OverridingScope(base=base, overrides=overrides)

        assert scope.base is base
        assert scope.overrides == overrides

    def test_overriding_scope_get_override(self):
        """Test get method returns override value."""
        key = StrBindKey("test")
        base = MScope(values={key: "base_value"})
        scope = OverridingScope(base=base, overrides={key: "override_value"})

        result = scope.get(key)
        assert result == Some("override_value")

    def test_overriding_scope_get_from_base(self):
        """Test get method falls back to base."""
        base_key = StrBindKey("base_only")
        base = MScope(values={base_key: "base_value"})
        scope = OverridingScope(base=base, overrides={})

        result = scope.get(base_key)
        assert result == Some("base_value")

    def test_overriding_scope_set_delegates(self):
        """Test set method delegates to base."""
        base = MScope(values={})
        scope = OverridingScope(base=base, overrides={})

        key = StrBindKey("new")
        value = "new_value"
        scope.set(key, value)

        # Should be set in base
        assert base.get(key) == Some(value)


class TestNoMappingError:
    """Test the NoMappingError class."""

    def test_no_mapping_error_creation(self):
        """Test creating NoMappingError."""
        error = NoMappingError("Test error message")

        assert isinstance(error, Exception)
        assert str(error) == "Test error message"


class TestDependencyResolver:
    """Test the DependencyResolver class."""

    def test_dependency_resolver_is_dataclass(self):
        """Test that DependencyResolver is a dataclass."""
        assert is_dataclass(DependencyResolver)

    def test_dependency_resolver_creation(self):
        """Test creating DependencyResolver instance."""
        mappings = {
            StrBindKey("a"): InjectedPure("value_a"),
            StrBindKey("b"): InjectedPure("value_b"),
        }

        resolver = DependencyResolver(mappings=mappings)

        assert resolver.mappings == mappings
        assert resolver.use_contextmanager is True  # default value

    def test_dependency_resolver_with_custom_flags(self):
        """Test DependencyResolver with custom flags."""
        resolver = DependencyResolver(mappings={}, use_contextmanager=False)

        assert resolver.use_contextmanager is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
