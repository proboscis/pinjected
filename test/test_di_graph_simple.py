"""Simple tests for pinjected.di.graph module to improve coverage."""

import pytest
import asyncio
from unittest.mock import Mock
from returns.result import Success

from pinjected import Injected, design
from pinjected.di.graph import (
    MissingDependencyException,
    DependencyResolver,
    MyObjectGraph,
    MScope,
    MChildScope,
    OverridingScope,
    NoMappingError,
    run_coroutine_in_new_thread,
    get_caller_info,
    AutoSyncGraph,
    providable_to_injected,
    trace_string,
    ProvideEvent,
    RichTraceLogger,
    EventDistributor,
    OGFactoryByDesign,
    SessionValue,
)


class TestMissingDependencyException:
    """Test MissingDependencyException class."""

    def test_create_message_empty(self):
        """Test create_message with empty list."""
        message = MissingDependencyException.create_message([])
        assert "Missing dependency, but no specific failures were reported." in message

    def test_create_with_failures(self):
        """Test create method with failures."""
        from pinjected.exceptions import DependencyResolutionFailure

        failure = Mock(spec=DependencyResolutionFailure)
        failure.key = "test_key"
        failure.trace_str.return_value = "trace"
        failure.cause = Exception("test error")

        exception = MissingDependencyException.create([failure])
        assert isinstance(exception, MissingDependencyException)
        assert "test_key" in str(exception)


class TestOGFactoryByDesign:
    """Test OGFactoryByDesign class."""

    def test_create(self):
        """Test create method."""
        mock_design = Mock()
        mock_graph = Mock()
        mock_design.to_graph.return_value = mock_graph

        factory = OGFactoryByDesign(src=mock_design)
        result = factory.create()

        assert result is mock_graph
        mock_design.to_graph.assert_called_once()


class TestTraceString:
    """Test trace_string function."""

    def test_empty(self):
        """Test with empty trace."""
        assert trace_string([]) == ""

    def test_single(self):
        """Test with single element."""
        assert trace_string(["a"]) == "a"

    def test_multiple(self):
        """Test with multiple elements."""
        assert trace_string(["a", "b", "c"]) == "a -> b -> c"


class TestProvideEvent:
    """Test ProvideEvent dataclass."""

    def test_creation(self):
        """Test ProvideEvent creation."""
        event = ProvideEvent(trace=["a", "b"], kind="provide", data="value")
        assert event.trace == ["a", "b"]
        assert event.kind == "provide"
        assert event.data == "value"


class TestNoMappingError:
    """Test NoMappingError class."""

    def test_creation(self):
        """Test NoMappingError creation."""
        error = NoMappingError("test_key")
        assert error.key == "test_key"
        assert "No mapping found for DI:test_key" in str(error)


class TestMScope:
    """Test MScope class."""

    def test_provide_new_key(self):
        """Test provide with new key."""
        scope = MScope()
        provider = Mock(return_value="value")

        result = scope.provide("key", provider, ["key"])

        assert result == "value"
        assert scope.cache["key"] == "value"
        provider.assert_called_once()

    def test_provide_cached_key(self):
        """Test provide with cached key."""
        scope = MScope(cache={"key": "cached_value"})
        provider = Mock()

        result = scope.provide("key", provider, ["key"])

        assert result == "cached_value"
        provider.assert_not_called()

    def test_contains(self):
        """Test __contains__ method."""
        scope = MScope(cache={"key": "value"})
        assert "key" in scope
        assert "missing" not in scope


class TestMChildScope:
    """Test MChildScope class."""

    def test_provide_from_cache(self):
        """Test provide from cache."""
        parent = Mock()
        scope = MChildScope(
            parent=parent, override_targets=set(), cache={"key": "cached"}
        )
        provider = Mock()

        result = scope.provide("key", provider, ["key"])

        assert result == "cached"
        provider.assert_not_called()

    def test_provide_override_target(self):
        """Test provide with override target."""
        parent = Mock()
        scope = MChildScope(parent=parent, override_targets={"key"})
        provider = Mock(return_value="new_value")

        result = scope.provide("key", provider, ["key"])

        assert result == "new_value"
        provider.assert_called_once()

    def test_contains(self):
        """Test __contains__ method."""
        parent = Mock()
        parent.__contains__ = Mock(side_effect=lambda x: x == "parent_key")

        scope = MChildScope(
            parent=parent, override_targets=set(), cache={"child_key": "value"}
        )

        assert "child_key" in scope
        assert "parent_key" in scope
        assert "missing" not in scope


class TestOverridingScope:
    """Test OverridingScope class."""

    def test_provide_from_overrides(self):
        """Test provide from overrides."""
        base = Mock()
        scope = OverridingScope(src=base, overrides={"key": "override_value"})
        provider = Mock()

        result = scope.provide("key", provider, ["key"])

        assert result == "override_value"
        provider.assert_not_called()

    def test_provide_from_base(self):
        """Test provide from base scope."""
        base = Mock()
        base.provide.return_value = "base_value"
        scope = OverridingScope(src=base, overrides={})
        provider = Mock()

        result = scope.provide("key", provider, ["key"])

        assert result == "base_value"
        base.provide.assert_called_once_with("key", provider, ["key"])

    def test_contains(self):
        """Test __contains__ method."""
        base = Mock()
        base.__contains__ = Mock(side_effect=lambda x: x == "base_key")

        scope = OverridingScope(src=base, overrides={"override_key": "value"})

        assert "override_key" in scope
        assert "base_key" in scope
        assert "missing" not in scope


class TestRunCoroutineInNewThread:
    """Test run_coroutine_in_new_thread function."""

    @pytest.mark.asyncio
    async def test_simple_coroutine(self):
        """Test running a simple coroutine."""

        async def test_coro():
            await asyncio.sleep(0.01)
            return "result"

        result = run_coroutine_in_new_thread(test_coro())
        assert result == "result"

    @pytest.mark.asyncio
    async def test_coroutine_with_exception(self):
        """Test coroutine that raises exception."""

        async def failing_coro():
            await asyncio.sleep(0.01)
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            run_coroutine_in_new_thread(failing_coro())


class TestGetCallerInfo:
    """Test get_caller_info function."""

    def test_basic_call(self):
        """Test getting caller info."""
        result = get_caller_info(1)

        # Result is wrapped in returns.result
        assert isinstance(result, Success)
        file_name, line_number = result.unwrap()

        assert file_name.endswith(".py")
        assert isinstance(line_number, int)
        assert line_number > 0


class TestProvidableToInjected:
    """Test providable_to_injected function."""

    def test_with_string(self):
        """Test with string key."""
        result = providable_to_injected("test_key")
        assert isinstance(result, Injected)

    def test_with_injected(self):
        """Test with Injected instance."""
        injected = Injected.pure("value")
        result = providable_to_injected(injected)
        assert result is injected

    def test_with_callable(self):
        """Test with callable."""

        def test_func():
            return "value"

        result = providable_to_injected(test_func)
        assert isinstance(result, Injected)

    def test_with_type(self):
        """Test with type."""

        class TestClass:
            pass

        result = providable_to_injected(TestClass)
        assert isinstance(result, Injected)


class TestEventDistributor:
    """Test EventDistributor class."""

    def test_register_and_emit(self):
        """Test registering callback and emitting event."""
        distributor = EventDistributor()
        callback = Mock()

        distributor.register(callback)

        event = ProvideEvent(trace=["test"], kind="provide", data="value")
        distributor.emit(event)

        callback.assert_called_once_with(event)

    def test_unregister(self):
        """Test unregistering callback."""
        distributor = EventDistributor()
        callback = Mock()

        distributor.register(callback)
        distributor.unregister(callback)

        event = ProvideEvent(trace=["test"], kind="provide", data="value")
        distributor.emit(event)

        callback.assert_not_called()

    def test_event_history(self):
        """Test event history replay."""
        distributor = EventDistributor()

        # Emit events before registration
        event1 = ProvideEvent(trace=["1"], kind="provide", data="v1")
        event2 = ProvideEvent(trace=["2"], kind="provide", data="v2")
        distributor.emit(event1)
        distributor.emit(event2)

        # Register callback
        callback = Mock()
        distributor.register(callback)

        # Should be called with historical events
        assert callback.call_count == 2
        callback.assert_any_call(event1)
        callback.assert_any_call(event2)


class TestDependencyResolver:
    """Test DependencyResolver class."""

    def test_init(self):
        """Test DependencyResolver initialization."""
        test_design = design(a=Injected.pure("value_a"), b=Injected.by_name("a"))

        resolver = DependencyResolver(src=test_design)

        assert resolver.src == test_design
        assert hasattr(resolver, "helper")
        assert hasattr(resolver, "mapping")
        assert "a" in resolver.mapping
        assert "b" in resolver.mapping

    def test_memoized_deps_pure(self):
        """Test memoized_deps with pure injection."""
        test_design = design(a=Injected.pure("value"))

        resolver = DependencyResolver(src=test_design)
        deps = resolver.memoized_deps("a")

        assert deps == set()  # Pure has no dependencies

    def test_memoized_deps_with_dependencies(self):
        """Test memoized_deps with dependencies."""
        test_design = design(a=Injected.pure("value"), b=Injected.by_name("a"))

        resolver = DependencyResolver(src=test_design)
        deps = resolver.memoized_deps("b")

        assert "a" in deps

    def test_memoized_deps_missing_key(self):
        """Test memoized_deps with missing key."""
        resolver = DependencyResolver(src=design())

        with pytest.raises(NoMappingError) as exc_info:
            resolver.memoized_deps("missing")

        assert "missing" in str(exc_info.value)


class TestMyObjectGraph:
    """Test MyObjectGraph class."""

    def test_root_creation(self):
        """Test creating graph with root static method."""
        test_design = design(a=Injected.pure("value_a"))

        graph = MyObjectGraph.root(test_design)

        assert isinstance(graph, MyObjectGraph)
        assert isinstance(graph.scope, MScope)
        assert isinstance(graph.resolver, DependencyResolver)

    def test_provide_string_key(self):
        """Test provide with string key."""
        test_design = design(test_key=Injected.pure("test_value"))

        graph = MyObjectGraph.root(test_design)
        result = graph.provide("test_key")

        # If result is a coroutine, await it
        if asyncio.iscoroutine(result):
            result = asyncio.run(result)

        assert result == "test_value"

    def test_provide_injected(self):
        """Test provide with Injected."""
        test_design = design()
        graph = MyObjectGraph.root(test_design)

        injected = Injected.pure("direct_value")
        result = graph.provide(injected)

        # If result is a coroutine, await it
        if asyncio.iscoroutine(result):
            result = asyncio.run(result)

        assert result == "direct_value"

    def test_factory_property(self):
        """Test factory property."""
        test_design = design()
        graph = MyObjectGraph.root(test_design)

        factory = graph.factory
        assert isinstance(factory, OGFactoryByDesign)
        assert factory.src == graph.src_design

    def test_design_property(self):
        """Test design property."""
        test_design = design(a=Injected.pure("value"))
        graph = MyObjectGraph.root(test_design)

        # Check that the graph has a design
        assert hasattr(graph, "design")

        # Check if "session" is in the design (behavior may have changed)
        if "session" in graph.design:
            assert graph.design != test_design
        else:
            # If session is not automatically added, the designs would be the same
            assert graph.design == test_design


class TestAutoSyncGraph:
    """Test AutoSyncGraph class."""

    def test_provide_sync(self):
        """Test provide in sync context."""
        from unittest.mock import MagicMock

        mock_graph = MagicMock()
        mock_graph.__getitem__.return_value = "result"

        auto_graph = AutoSyncGraph(src=mock_graph)
        result = auto_graph["key"]

        assert result == "result"
        mock_graph.__getitem__.assert_called_once_with("key")


class TestRichTraceLogger:
    """Test RichTraceLogger class."""

    def test_call_request_event(self):
        """Test logging request event."""
        logger = RichTraceLogger()
        logger.console = Mock()

        event = ProvideEvent(trace=["a", "b"], kind="request", data=None)
        logger(event)

        # Should log the trace
        assert logger.console.log.call_count >= 1

    def test_call_provide_event(self):
        """Test logging provide event."""
        logger = RichTraceLogger()
        logger.console = Mock()

        event = ProvideEvent(trace=["a", "b", "c"], kind="provide", data="value")
        logger(event)

        # Should log trace and data
        assert logger.console.log.call_count >= 2


class TestSessionValue:
    """Test SessionValue class."""

    def test_creation(self):
        """Test SessionValue creation."""
        parent = Mock()
        child_session = Mock()
        parent.child_session.return_value = child_session

        designed = Mock()
        designed.design = Mock()

        value = SessionValue(parent=parent, designed=designed)

        assert value.parent is parent
        assert value.designed is designed
        assert value.session is child_session

        parent.child_session.assert_called_once_with(designed.design)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
