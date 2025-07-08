"""Tests to boost coverage for pinjected.di.graph module."""

import pytest
from unittest.mock import Mock
from pinjected.di.graph import (
    MissingDependencyException,
    OGFactoryByDesign,
    MScope,
    ProvideEvent,
    EventDistributor,
    trace_string,
    NoMappingError,
)
from pinjected.exceptions import DependencyResolutionFailure


class TestMissingDependencyException:
    """Tests for MissingDependencyException class."""

    def test_create_message_no_deps(self):
        """Test create_message with empty dependency list."""
        message = MissingDependencyException.create_message([])
        assert "Missing dependency, but no specific failures were reported." in message

    def test_create_message_with_deps(self):
        """Test create_message with dependency failures."""
        # Create mock failure
        failure = Mock(spec=DependencyResolutionFailure)
        failure.key = "test_key"
        failure.trace_str.return_value = "dep1 -> dep2 -> test_key"
        failure.cause = Mock()
        failure.cause.key = "root_cause_key"

        message = MissingDependencyException.create_message([failure])

        assert "Missing Dependencies" in message
        assert "test_key" in message
        assert "dep1 -> dep2 -> test_key" in message
        assert "root_cause_key" in message

    def test_create_message_with_non_key_cause(self):
        """Test create_message when cause doesn't have key attribute."""
        failure = Mock(spec=DependencyResolutionFailure)
        failure.key = "test_key"
        failure.trace_str.return_value = "trace"
        failure.cause = Exception("Some error")

        message = MissingDependencyException.create_message([failure])
        assert "Some error" in message

    def test_create_exception(self):
        """Test creating exception with create method."""
        deps = []
        exc = MissingDependencyException.create(deps)
        assert isinstance(exc, MissingDependencyException)


class TestOGFactoryByDesign:
    """Tests for OGFactoryByDesign class."""

    def test_create(self):
        """Test create method returns graph from design."""
        mock_design = Mock()
        mock_graph = Mock()
        mock_design.to_graph.return_value = mock_graph

        factory = OGFactoryByDesign(src=mock_design)
        result = factory.create()

        assert result == mock_graph
        mock_design.to_graph.assert_called_once()


class TestProvideEvent:
    """Tests for ProvideEvent class."""

    def test_provide_event_creation(self):
        """Test creating ProvideEvent instances."""
        event1 = ProvideEvent(trace=["a", "b"], kind="request")
        assert event1.trace == ["a", "b"]
        assert event1.kind == "request"
        assert event1.data is None

        event2 = ProvideEvent(trace=["x"], kind="provide", data="result")
        assert event2.trace == ["x"]
        assert event2.kind == "provide"
        assert event2.data == "result"


class TestMScope:
    """Tests for MScope class."""

    def test_mscope_init_default(self):
        """Test MScope initialization with defaults."""
        scope = MScope()
        assert scope.cache == {}
        assert scope._trace_logger is not None

    def test_mscope_init_with_logger(self):
        """Test MScope initialization with custom logger."""
        logger = Mock()
        scope = MScope(_trace_logger=logger)
        assert scope.trace_logger == logger

    def test_mscope_contains(self):
        """Test __contains__ method."""
        scope = MScope()
        scope.cache["key1"] = "value1"

        assert "key1" in scope
        assert "key2" not in scope

    def test_mscope_getstate_raises(self):
        """Test __getstate__ raises NotImplementedError."""
        scope = MScope()
        with pytest.raises(NotImplementedError, match="MScope is not serializable"):
            scope.__getstate__()

    def test_mscope_provide_cached(self):
        """Test provide returns cached value."""
        logger = Mock()
        scope = MScope(_trace_logger=logger)
        scope.cache["key"] = "cached_value"

        provider = Mock()
        result = scope.provide("key", provider, ["key"])

        assert result == "cached_value"
        provider.assert_not_called()
        # Should log request and provide events
        assert logger.call_count == 2

    def test_mscope_provide_new(self):
        """Test provide computes new value."""
        logger = Mock()
        scope = MScope(_trace_logger=logger)

        provider = Mock(return_value="new_value")
        result = scope.provide("key", provider, ["key"])

        assert result == "new_value"
        assert scope.cache["key"] == "new_value"
        provider.assert_called_once()
        # Should log request and provide events
        assert logger.call_count == 2


class TestEventDistributor:
    """Tests for EventDistributor class."""

    def test_event_distributor_init(self):
        """Test EventDistributor initialization."""
        dist = EventDistributor()
        assert dist.callbacks == []
        assert dist.event_history == []

    def test_register_callback(self):
        """Test registering callback."""
        dist = EventDistributor()
        callback = Mock()

        # Add some events to history
        dist.emit("event1")
        dist.emit("event2")

        # Register callback - should receive historical events
        dist.register(callback)

        assert callback in dist.callbacks
        assert callback.call_count == 2
        callback.assert_any_call("event1")
        callback.assert_any_call("event2")

    def test_unregister_callback(self):
        """Test unregistering callback."""
        dist = EventDistributor()
        callback = Mock()

        dist.register(callback)
        assert callback in dist.callbacks

        dist.unregister(callback)
        assert callback not in dist.callbacks

    def test_emit_event(self):
        """Test emitting events."""
        dist = EventDistributor()
        callback1 = Mock()
        callback2 = Mock()

        dist.register(callback1)
        dist.register(callback2)

        dist.emit("new_event")

        assert "new_event" in dist.event_history
        callback1.assert_called_with("new_event")
        callback2.assert_called_with("new_event")


class TestUtilityFunctions:
    """Tests for utility functions."""

    def test_trace_string(self):
        """Test trace_string function."""
        assert trace_string(["a"]) == "a"
        assert trace_string(["a", "b", "c"]) == "a -> b -> c"
        assert trace_string([]) == ""


class TestNoMappingError:
    """Tests for NoMappingError class."""

    def test_no_mapping_error(self):
        """Test NoMappingError creation."""
        error = NoMappingError("test_key")
        assert "No mapping found for DI:test_key" in str(error)
        assert error.key == "test_key"
