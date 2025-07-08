"""Simple tests for di/graph.py module to improve coverage."""

import pytest
from unittest.mock import Mock
from dataclasses import is_dataclass

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


class TestMissingDependencyException:
    """Test the MissingDependencyException class."""

    def test_create_message_empty(self):
        """Test create_message with empty list."""
        message = MissingDependencyException.create_message([])

        assert isinstance(message, str)
        assert "Missing dependency" in message

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
        assert "Missing Dependencies" in message


class TestOGFactoryByDesign:
    """Test the OGFactoryByDesign class."""

    def test_og_factory_by_design_is_dataclass(self):
        """Test that OGFactoryByDesign is a dataclass."""
        assert is_dataclass(OGFactoryByDesign)

    def test_og_factory_by_design_creation(self):
        """Test creating OGFactoryByDesign instance."""
        mock_design = Mock()
        factory = OGFactoryByDesign(src=mock_design)

        assert factory.src is mock_design

    def test_create_graph(self):
        """Test create_graph method."""
        mock_design = Mock()
        mock_design.to_graph.return_value = Mock()

        factory = OGFactoryByDesign(src=mock_design)
        graph = factory.create()

        mock_design.to_graph.assert_called_once()
        assert graph is mock_design.to_graph.return_value


class TestProvideEvent:
    """Test the ProvideEvent dataclass."""

    def test_provide_event_is_dataclass(self):
        """Test that ProvideEvent is a dataclass."""
        assert is_dataclass(ProvideEvent)

    def test_provide_event_creation(self):
        """Test creating ProvideEvent instance."""
        trace = ["key1", "key2"]
        kind = "provide"
        data = {"result": "test_data"}

        event = ProvideEvent(trace=trace, kind=kind, data=data)

        assert event.trace == trace
        assert event.kind == kind
        assert event.data == data


class TestRichTraceLogger:
    """Test the RichTraceLogger class."""

    def test_rich_trace_logger_is_dataclass(self):
        """Test that RichTraceLogger is a dataclass."""
        assert is_dataclass(RichTraceLogger)

    def test_rich_trace_logger_creation(self):
        """Test creating RichTraceLogger instance."""
        logger = RichTraceLogger()

        assert hasattr(logger, "console")
        assert logger.console is not None
        # RichTraceLogger is callable
        assert callable(logger)

    def test_rich_trace_logger_with_values(self):
        """Test RichTraceLogger with custom console."""
        from rich.console import Console

        mock_console = Mock(spec=Console)
        logger = RichTraceLogger(console=mock_console)

        assert logger.console is mock_console

        # Test calling the logger with a ProvideEvent
        event = ProvideEvent(trace=["A", "B"], kind="request", data=None)
        logger(event)

        # Verify console.log was called
        mock_console.log.assert_called()


class TestMScope:
    """Test the MScope class."""

    def test_mscope_is_dataclass(self):
        """Test that MScope is a dataclass."""
        assert is_dataclass(MScope)

    def test_mscope_creation(self):
        """Test creating MScope instance."""
        scope = MScope()

        assert hasattr(scope, "cache")
        assert isinstance(scope.cache, dict)
        assert hasattr(scope, "_trace_logger")
        assert hasattr(scope, "trace_logger")

    def test_mscope_provide_existing(self):
        """Test provide method for existing key in cache."""
        key = "test"
        value = "test_value"
        scope = MScope()
        scope.cache[key] = value

        # Mock provider function
        provider = Mock(return_value="new_value")

        result = scope.provide(key, provider, [key])

        # Should return cached value without calling provider
        assert result == value
        provider.assert_not_called()

    def test_mscope_provide_new(self):
        """Test provide method for new key."""
        key = "new"
        value = "new_value"
        scope = MScope()

        # Mock provider function
        provider = Mock(return_value=value)

        result = scope.provide(key, provider, [key])

        # Should call provider and cache the result
        assert result == value
        provider.assert_called_once()
        assert scope.cache[key] == value

    def test_mscope_contains(self):
        """Test __contains__ method."""
        scope = MScope()
        key = "test"

        assert key not in scope

        scope.cache[key] = "value"

        assert key in scope


class TestMChildScope:
    """Test the MChildScope class."""

    def test_mchild_scope_is_dataclass(self):
        """Test that MChildScope is a dataclass."""
        assert is_dataclass(MChildScope)

    def test_mchild_scope_creation(self):
        """Test creating MChildScope instance."""
        parent = MScope()
        parent.cache["parent"] = "parent_value"
        override_targets = {"override_key"}

        scope = MChildScope(parent=parent, override_targets=override_targets)

        assert scope.parent is parent
        assert scope.override_targets == override_targets
        assert isinstance(scope.cache, dict)

    def test_mchild_scope_provide_from_parent(self):
        """Test provide method falls back to parent."""
        parent = MScope()
        parent.cache["parent_key"] = "parent_value"

        child = MChildScope(parent=parent, override_targets=set())

        # Mock provider
        provider = Mock(return_value="new_value")

        # Should get from parent without calling provider
        result = child.provide("parent_key", provider, ["parent_key"])
        assert result == "parent_value"
        provider.assert_not_called()

    def test_mchild_scope_override_parent(self):
        """Test child overrides parent for keys in override_targets."""
        key = "shared"
        parent = MScope()
        parent.cache[key] = "parent_value"

        # Key is in override_targets, so child should provide new value
        child = MChildScope(parent=parent, override_targets={key})

        provider = Mock(return_value="child_value")
        result = child.provide(key, provider, [key])

        # Should call provider and use child value
        assert result == "child_value"
        provider.assert_called_once()
        assert child.cache[key] == "child_value"


class TestOverridingScope:
    """Test the OverridingScope class."""

    def test_overriding_scope_is_dataclass(self):
        """Test that OverridingScope is a dataclass."""
        assert is_dataclass(OverridingScope)

    def test_overriding_scope_creation(self):
        """Test creating OverridingScope instance."""
        src = MScope()
        src.cache["base"] = "base_value"
        overrides = {"override": "override_value"}

        scope = OverridingScope(src=src, overrides=overrides)

        assert scope.src is src
        assert scope.overrides == overrides

    def test_overriding_scope_provide_override(self):
        """Test provide method returns override value."""
        key = "test"
        src = MScope()
        src.cache[key] = "base_value"

        scope = OverridingScope(src=src, overrides={key: "override_value"})

        provider = Mock(return_value="new_value")
        result = scope.provide(key, provider, [key])

        # Should return override without calling provider
        assert result == "override_value"
        provider.assert_not_called()

    def test_overriding_scope_provide_from_src(self):
        """Test provide method falls back to src."""
        base_key = "base_only"
        src = MScope()
        src.cache[base_key] = "base_value"

        scope = OverridingScope(src=src, overrides={})

        provider = Mock(return_value="new_value")
        result = scope.provide(base_key, provider, [base_key])

        # Should get from src
        assert result == "base_value"
        provider.assert_not_called()

    def test_overriding_scope_contains(self):
        """Test __contains__ method."""
        src = MScope()
        src.cache["base_key"] = "value"

        scope = OverridingScope(src=src, overrides={"override_key": "value"})

        # Should find in overrides
        assert "override_key" in scope
        # Should find in src
        assert "base_key" in scope
        # Should not find missing key
        assert "missing_key" not in scope


class TestNoMappingError:
    """Test the NoMappingError class."""

    def test_no_mapping_error_creation(self):
        """Test creating NoMappingError."""
        key = "test_key"
        error = NoMappingError(key)

        assert isinstance(error, Exception)
        assert str(error) == f"No mapping found for DI:{key}"
        assert error.key == key


class TestDependencyResolver:
    """Test the DependencyResolver class."""

    def test_dependency_resolver_is_dataclass(self):
        """Test that DependencyResolver is a dataclass."""
        assert is_dataclass(DependencyResolver)

    def test_dependency_resolver_creation(self):
        """Test creating DependencyResolver instance."""
        from pinjected.di.design import Design

        # Create a mock Design with bindings
        mock_design = Mock(spec=Design)
        mock_design.bindings = {}  # Empty bindings dict

        resolver = DependencyResolver(src=mock_design)

        assert resolver.src is mock_design
        assert hasattr(resolver, "helper")
        assert hasattr(resolver, "mapping")

    def test_dependency_resolver_to_injected(self):
        """Test _to_injected method."""
        from pinjected.di.design import Design

        # Create a mock Design with bindings
        mock_design = Mock(spec=Design)
        mock_design.bindings = {}

        resolver = DependencyResolver(src=mock_design)

        # Test with a simple providable
        result = resolver._to_injected("test_string")
        assert result is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
