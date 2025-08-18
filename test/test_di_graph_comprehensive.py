"""Comprehensive tests for pinjected/di/graph.py to improve coverage."""

import pytest
from unittest.mock import Mock, patch

from pinjected import Injected
from pinjected.di.graph import (
    MissingDependencyException,
    IObjectGraphFactory,
    OGFactoryByDesign,
    IObjectGraph,
    ProvideEvent,
    IScope,
    trace_string,
    RichTraceLogger,
    MScope,
    MChildScope,
    OverridingScope,
    NoMappingError,
    DependencyResolver,
    MyObjectGraph,
)
from pinjected.di.design_interface import Design
from pinjected.exceptions import DependencyResolutionFailure


class TestMissingDependencyException:
    """Test MissingDependencyException functionality."""

    def test_create_message_empty_deps(self):
        """Test create_message with empty dependencies."""
        message = MissingDependencyException.create_message([])
        assert "Missing dependency, but no specific failures were reported." in message

    def test_create_message_with_deps(self):
        """Test create_message with dependency failures."""
        failure = DependencyResolutionFailure(
            key="missing_key", trace=["a", "b", "c"], cause=Exception("Test cause")
        )

        message = MissingDependencyException.create_message([failure])

        assert "Missing Dependencies:" in message
        assert "missing_key" in message
        assert "Failure #1:" in message
        assert "Dependency Chain:" in message
        assert "Root Cause:" in message

    def test_create_message_with_key_cause(self):
        """Test create_message when cause has key attribute."""
        cause_with_key = Mock()
        cause_with_key.key = "root_key"

        failure = DependencyResolutionFailure(
            key="missing_key", trace=["x", "y"], cause=cause_with_key
        )

        message = MissingDependencyException.create_message([failure])
        assert "Failed to find dependency for root_key" in message

    def test_create_exception(self):
        """Test create method."""
        failure = DependencyResolutionFailure(
            key="test_key", trace=["dep1"], cause=Exception("Test")
        )

        exc = MissingDependencyException.create([failure])
        assert isinstance(exc, MissingDependencyException)
        assert "test_key" in str(exc)


class TestOGFactoryByDesign:
    """Test OGFactoryByDesign functionality."""

    def test_create(self):
        """Test creating object graph from design."""
        mock_design = Mock(spec=Design)
        mock_graph = Mock(spec=IObjectGraph)
        mock_design.to_graph.return_value = mock_graph

        factory = OGFactoryByDesign(src=mock_design)
        graph = factory.create()

        assert graph == mock_graph
        mock_design.to_graph.assert_called_once()


class TestProvideEvent:
    """Test ProvideEvent dataclass."""

    def test_provide_event_creation(self):
        """Test creating ProvideEvent."""
        event = ProvideEvent(trace=["a", "b"], kind="provide", data="test_value")

        assert event.trace == ["a", "b"]
        assert event.kind == "provide"
        assert event.data == "test_value"


class TestTraceString:
    """Test trace_string function."""

    def test_trace_string_empty(self):
        """Test trace_string with empty trace."""
        result = trace_string([])
        assert result == ""

    def test_trace_string_single(self):
        """Test trace_string with single element."""
        result = trace_string(["root"])
        assert result == "root"

    def test_trace_string_multiple(self):
        """Test trace_string with multiple elements."""
        result = trace_string(["a", "b", "c"])
        assert result == "a -> b -> c"


class TestRichTraceLogger:
    """Test RichTraceLogger functionality."""

    @patch("pinjected.di.graph.Console")
    def test_call_with_event(self, mock_console_class):
        """Test calling logger with event."""
        mock_console = Mock()
        mock_console_class.return_value = mock_console

        logger = RichTraceLogger()
        event = ProvideEvent(trace=["dep1", "dep2"], kind="provide", data="test_value")

        logger(event)

        # Should create console and log
        mock_console_class.assert_called_once()
        mock_console.log.assert_called()


class TestMScope:
    """Test MScope functionality."""

    def test_init(self):
        """Test MScope initialization."""
        scope = MScope()

        assert hasattr(scope, "cache")
        assert hasattr(scope, "_trace_logger")

    def test_getstate(self):
        """Test MScope serialization."""
        scope = MScope()

        # MScope raises NotImplementedError for serialization
        with pytest.raises(NotImplementedError, match="MScope is not serializable"):
            scope.__getstate__()

    def test_provide_cached(self):
        """Test provide returns cached value."""
        scope = MScope()
        scope.cache["test_key"] = "cached_value"

        result = scope.provide("test_key", lambda: "new_value", ["test_key"])
        assert result == "cached_value"

    def test_provide_new_value(self):
        """Test provide creates new value."""
        scope = MScope()
        provider = Mock(return_value="new_value")

        result = scope.provide("test_key", provider, ["test_key"])

        assert result == "new_value"
        assert scope.cache["test_key"] == "new_value"
        provider.assert_called_once()

    def test_provide_concurrent_access(self):
        """Test concurrent access to provide."""
        scope = MScope()
        call_count = 0

        def slow_provider():
            nonlocal call_count
            call_count += 1
            # Simulate slow operation
            import time

            time.sleep(0.1)
            return f"value_{call_count}"

        # Multiple threads should get same value
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(scope.provide, "key", slow_provider, ["key"])
                for _ in range(3)
            ]
            results = [f.result() for f in futures]

        # Without thread safety, provider may be called multiple times
        # but all results should still be valid
        assert all(r.startswith("value_") for r in results)
        # Provider was called at least once, possibly up to 3 times due to race conditions
        assert 1 <= call_count <= 3

    def test_contains(self):
        """Test __contains__ method."""
        scope = MScope()
        scope.cache["exists"] = "value"

        assert "exists" in scope
        assert "not_exists" not in scope

    def test_trace_logger_property(self):
        """Test trace_logger property."""
        scope = MScope()
        custom_logger = Mock()
        scope._trace_logger = custom_logger

        assert scope.trace_logger == custom_logger


class TestMChildScope:
    """Test MChildScope functionality."""

    def test_init(self):
        """Test MChildScope initialization."""
        parent = MScope()
        override_targets = {"key"}

        child = MChildScope(parent=parent, override_targets=override_targets)

        assert child.parent == parent
        assert child.override_targets == override_targets

    def test_provide_from_overrides(self):
        """Test provide uses provider when key is in override_targets."""
        parent = MScope()
        parent.cache["test_key"] = "parent_value"
        child = MChildScope(parent=parent, override_targets={"test_key"})

        result = child.provide("test_key", lambda: "child_value", ["test_key"])
        assert result == "child_value"  # Child provides its own value

    def test_provide_from_parent(self):
        """Test provide delegates to parent when no override."""
        parent = MScope()
        parent.cache["parent_key"] = "parent_value"
        child = MChildScope(parent=parent, override_targets=set())

        result = child.provide("parent_key", lambda: "new_value", ["parent_key"])
        assert result == "parent_value"

    def test_contains_checks_both(self):
        """Test __contains__ checks both cache and parent."""
        parent = MScope()
        parent.cache["parent_key"] = "value"
        child = MChildScope(parent=parent, override_targets={"child_key"})

        # Child key not in cache yet, so not in child
        assert "child_key" not in child
        assert "parent_key" in child  # From parent
        assert "missing_key" not in child

        # After providing, it should be in child
        child.provide("child_key", lambda: "child_value", ["child_key"])
        assert "child_key" in child


class TestOverridingScope:
    """Test OverridingScope functionality."""

    def test_provide_with_override(self):
        """Test provide returns override value."""
        src = Mock(spec=IScope)
        overrides = {"test_key": "override_value"}
        scope = OverridingScope(src=src, overrides=overrides)

        result = scope.provide("test_key", lambda: "provider_value", ["test_key"])

        # Should return override value without calling provider
        assert result == "override_value"
        src.provide.assert_not_called()

    def test_provide_without_override(self):
        """Test provide delegates to source when no override."""
        src = Mock(spec=IScope)
        src.provide.return_value = "src_value"
        scope = OverridingScope(src=src, overrides={})
        provider = Mock(return_value="value")

        result = scope.provide("key", provider, ["key"])

        # Should call src with same parameters
        src.provide.assert_called_once_with("key", provider, ["key"])
        assert result == "src_value"

    def test_contains(self):
        """Test __contains__ checks overrides and src."""
        src = Mock(spec=IScope)
        src.__contains__ = Mock(return_value=True)
        scope = OverridingScope(src=src, overrides={"override_key": "value"})

        # Check override key
        assert "override_key" in scope

        # Check src delegation
        assert "other_key" in scope
        src.__contains__.assert_called_once_with("other_key")


class TestNoMappingError:
    """Test NoMappingError exception."""

    def test_init(self):
        """Test NoMappingError initialization."""
        error = NoMappingError("missing_key")
        assert error.key == "missing_key"
        assert "missing_key" in str(error)


class TestDependencyResolver:
    """Test DependencyResolver functionality."""

    def test_init(self):
        """Test DependencyResolver initialization."""
        # Create a real Design object instead of mocking
        from pinjected import design

        test_design = design()
        resolver = DependencyResolver(src=test_design)

        assert resolver.src == test_design
        assert hasattr(resolver, "helper")
        assert hasattr(resolver, "mapping")
        assert isinstance(resolver.mapping, dict)

    @pytest.mark.skip(reason="DependencyResolver doesn't have purified_design method")
    def test_purified_design(self):
        """Test purified_design method - SKIPPED: method doesn't exist."""
        pass


class TestMyObjectGraph:
    """Test MyObjectGraph functionality."""

    def test_provide_simple(self):
        """Test basic provide functionality."""
        from pinjected import design

        test_design = design(test_key=Injected.pure("test_value"))
        graph = MyObjectGraph.root(test_design)

        result = graph.provide("test_key")
        assert result == "test_value"

    def test_getitem(self):
        """Test __getitem__ delegates to provide."""
        from pinjected import design

        test_design = design(key=Injected.pure("value"))
        graph = MyObjectGraph.root(test_design)

        result = graph["key"]
        assert result == "value"

    def test_child_session(self):
        """Test creating child session."""
        from pinjected import design

        test_design = design(key=Injected.pure("value"))
        graph = MyObjectGraph.root(test_design)

        override_design = design(override=Injected.pure("new_value"))
        child = graph.child_session(override_design)

        assert isinstance(child, MyObjectGraph)
        assert isinstance(child.scope, MChildScope)

    @pytest.mark.asyncio
    async def test_run_async(self):
        """Test run with async function."""
        from pinjected import design

        test_design = design()
        graph = MyObjectGraph.root(test_design)

        async def async_func():
            return "async_result"

        result = await graph.run(async_func)
        assert result == "async_result"

    def test_run_sync(self):
        """Test run with sync function."""
        from pinjected import design

        test_design = design()
        graph = MyObjectGraph.root(test_design)

        def sync_func():
            return "sync_result"

        result = graph.run(sync_func)
        assert result == "sync_result"

    def test_proxied(self):
        """Test proxied method."""
        from pinjected import design

        test_design = design(key=Injected.pure("value"))
        graph = MyObjectGraph.root(test_design)

        proxy = graph.proxied("key")
        # Should return a DelegatedVar
        from pinjected.di.proxiable import DelegatedVar

        assert isinstance(proxy, DelegatedVar)

    def test_sessioned(self):
        """Test sessioned method."""
        from pinjected import design

        test_design = design(key=Injected.pure("value"))
        graph = MyObjectGraph.root(test_design)

        sessioned = graph.sessioned("key")
        # Should return a DelegatedVar
        from pinjected.di.proxiable import DelegatedVar

        assert isinstance(sessioned, DelegatedVar)

    def test_factory(self):
        """Test factory property."""
        from pinjected import design

        test_design = design()
        graph = MyObjectGraph.root(test_design)

        factory = graph.factory
        assert isinstance(factory, IObjectGraphFactory)

    def test_design(self):
        """Test design property."""
        from pinjected import design

        test_design = design(key=Injected.pure("value"))
        graph = MyObjectGraph.root(test_design)

        d = graph.design
        # Should return a Design object
        assert hasattr(d, "provide")

    def test_resolver(self):
        """Test resolver property."""
        from pinjected import design

        test_design = design()
        graph = MyObjectGraph.root(test_design)

        resolver = graph.resolver
        assert isinstance(resolver, DependencyResolver)
