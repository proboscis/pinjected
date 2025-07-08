"""Tests for di/graph.py module."""

import pytest
from unittest.mock import Mock
import asyncio
from dataclasses import is_dataclass
from returns.result import Success, Result

from pinjected.di.graph import (
    MissingDependencyException,
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
    run_coroutine_in_new_thread,
    get_caller_info,
    providable_to_injected,
    EventDistributor,
    SessionValue,
)
from pinjected.exceptions import DependencyResolutionFailure
from pinjected import Injected
from pinjected.di.designed import Designed
from pinjected.di.proxiable import DelegatedVar
from pinjected.di.injected import InjectedByName


class TestMissingDependencyException:
    """Test MissingDependencyException class."""

    def test_create_message_empty_list(self):
        """Test create_message with empty list."""
        message = MissingDependencyException.create_message([])
        assert "Missing dependency, but no specific failures were reported." in message

    def test_create_message_with_failures(self):
        """Test create_message with dependency failures."""
        # Create mock failures
        failure1 = Mock(spec=DependencyResolutionFailure)
        failure1.key = "key1"
        failure1.trace_str.return_value = "parent -> key1"
        failure1.cause = Mock(key="root_key")

        failure2 = Mock(spec=DependencyResolutionFailure)
        failure2.key = "key2"
        failure2.trace_str.return_value = "parent -> middle -> key2"
        failure2.cause = Exception("Some error")

        message = MissingDependencyException.create_message([failure1, failure2])

        assert "Missing Dependencies" in message
        assert "key1" in message
        assert "key2" in message
        assert "parent -> key1" in message
        assert "parent -> middle -> key2" in message
        assert "Root Cause: Failed to find dependency for root_key" in message
        assert "Root Cause: Some error" in message
        assert "Use the 'describe' command" in message

    def test_create(self):
        """Test create method."""
        failure = Mock(spec=DependencyResolutionFailure)
        failure.key = "test_key"
        failure.trace_str.return_value = "trace"
        failure.cause = Exception("test error")

        exception = MissingDependencyException.create([failure])

        assert isinstance(exception, MissingDependencyException)
        assert "test_key" in str(exception)


class TestOGFactoryByDesign:
    """Test OGFactoryByDesign class."""

    def test_is_dataclass(self):
        """Test that OGFactoryByDesign is a dataclass."""
        assert is_dataclass(OGFactoryByDesign)

    def test_create(self):
        """Test create method."""
        mock_design = Mock()
        mock_graph = Mock(spec=IObjectGraph)
        mock_design.to_graph.return_value = mock_graph

        factory = OGFactoryByDesign(src=mock_design)
        result = factory.create()

        assert result is mock_graph
        mock_design.to_graph.assert_called_once()


class TestTraceString:
    """Test trace_string function."""

    def test_trace_string_empty(self):
        """Test trace_string with empty list."""
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
    """Test RichTraceLogger class."""

    def test_is_dataclass(self):
        """Test that RichTraceLogger is a dataclass."""
        assert is_dataclass(RichTraceLogger)

    def test_log(self):
        """Test call method."""
        logger = RichTraceLogger()
        # Mock the console on the instance
        logger.console = Mock()

        # Test request event
        event = ProvideEvent(trace=["step1", "step2"], kind="request", data=None)
        logger(event)

        # Verify console.log was called
        assert logger.console.log.call_count >= 1

        # Test provide event
        event2 = ProvideEvent(trace=["a", "b", "c"], kind="provide", data="test_data")
        logger(event2)

        # Should have more log calls now
        assert logger.console.log.call_count >= 3


class TestProvideEvent:
    """Test ProvideEvent class."""

    def test_is_dataclass(self):
        """Test that ProvideEvent is a dataclass."""
        assert is_dataclass(ProvideEvent)

    def test_creation(self):
        """Test ProvideEvent creation."""
        event = ProvideEvent(trace=["key1", "key2"], kind="provide", data="test_value")
        assert event.trace == ["key1", "key2"]
        assert event.kind == "provide"
        assert event.data == "test_value"


class TestMScope:
    """Test MScope class."""

    def test_is_dataclass(self):
        """Test that MScope is a dataclass."""
        assert is_dataclass(MScope)

    def test_provide_new_key(self):
        """Test provide with new key."""
        scope = MScope()
        mock_provider = Mock(return_value="test_value")

        result = scope.provide("key1", mock_provider, ["key1"])

        assert result == "test_value"
        assert scope.cache["key1"] == "test_value"
        mock_provider.assert_called_once()

    def test_provide_existing_key(self):
        """Test provide with existing key in cache."""
        scope = MScope(cache={"key1": "cached_value"})
        mock_provider = Mock(return_value="new_value")

        result = scope.provide("key1", mock_provider, ["key1"])

        assert result == "cached_value"
        # Provider should not be called for cached key
        mock_provider.assert_not_called()

    def test_contains(self):
        """Test __contains__ method."""
        scope = MScope(cache={"key1": "value1"})

        assert "key1" in scope
        assert "key2" not in scope


class TestMChildScope:
    """Test MChildScope class."""

    def test_is_dataclass(self):
        """Test that MChildScope is a dataclass."""
        assert is_dataclass(MChildScope)

    def test_provide_from_cache(self):
        """Test provide from cache first."""
        parent = Mock(spec=IScope)
        parent.__contains__ = Mock(return_value=True)
        parent.provide = Mock(return_value="parent_value")

        scope = MChildScope(
            parent=parent, override_targets=set(), cache={"key": "child_value"}
        )
        mock_provider = Mock(return_value="new_value")

        result = scope.provide("key", mock_provider, ["key"])

        assert result == "child_value"
        mock_provider.assert_not_called()
        parent.provide.assert_not_called()

    def test_provide_from_parent(self):
        """Test provide from parent when not in cache or override targets."""
        parent = Mock(spec=IScope)
        parent.__contains__ = Mock(return_value=True)
        parent.provide = Mock(return_value="parent_value")

        scope = MChildScope(parent=parent, override_targets=set())
        mock_provider = Mock(return_value="new_value")

        result = scope.provide("key", mock_provider, ["key"])

        assert result == "parent_value"
        assert scope.cache["key"] == "parent_value"
        parent.provide.assert_called_once_with("key", mock_provider, ["key"])

    def test_provide_override_target(self):
        """Test provide when key is in override_targets."""
        parent = Mock(spec=IScope)
        scope = MChildScope(parent=parent, override_targets={"key"})
        mock_provider = Mock(return_value="override_value")

        result = scope.provide("key", mock_provider, ["key"])

        assert result == "override_value"
        assert scope.cache["key"] == "override_value"
        mock_provider.assert_called_once()

    def test_contains(self):
        """Test __contains__ method."""
        parent = Mock(spec=IScope)
        parent.__contains__ = Mock(side_effect=lambda x: x == "parent_key")

        scope = MChildScope(
            parent=parent, override_targets=set(), cache={"child_key": "value"}
        )

        assert "child_key" in scope
        assert "parent_key" in scope
        assert "missing_key" not in scope


class TestOverridingScope:
    """Test OverridingScope class."""

    def test_provide_from_overrides(self):
        """Test provide from overrides."""
        base_scope = Mock(spec=IScope)
        base_scope.provide = Mock(return_value="base_value")

        scope = OverridingScope(src=base_scope, overrides={"key1": "override_value"})
        mock_provider = Mock(return_value="provider_value")

        result = scope.provide("key1", mock_provider, ["key1"])

        assert result == "override_value"
        # Should not call base scope for overridden key
        base_scope.provide.assert_not_called()

    def test_provide_from_base(self):
        """Test provide from base scope when not in overrides."""
        base_scope = Mock(spec=IScope)
        base_scope.provide = Mock(return_value="base_value")

        scope = OverridingScope(src=base_scope, overrides={"key1": "override_value"})
        mock_provider = Mock(return_value="provider_value")

        result = scope.provide("key2", mock_provider, ["key2"])

        assert result == "base_value"
        base_scope.provide.assert_called_once_with("key2", mock_provider, ["key2"])

    def test_contains(self):
        """Test __contains__ method."""
        base_scope = Mock(spec=IScope)
        base_scope.__contains__ = Mock(side_effect=lambda x: x == "base_key")

        scope = OverridingScope(src=base_scope, overrides={"override_key": "value"})

        assert "override_key" in scope
        assert "base_key" in scope
        assert "missing_key" not in scope


class TestNoMappingError:
    """Test NoMappingError class."""

    def test_creation(self):
        """Test NoMappingError creation."""
        error = NoMappingError("test_key")

        assert error.key == "test_key"
        assert "No mapping found for DI:test_key" in str(error)


class TestRunCoroutineInNewThread:
    """Test run_coroutine_in_new_thread function."""

    @pytest.mark.asyncio
    async def test_run_coroutine(self):
        """Test running coroutine in new thread."""

        async def test_coro():
            await asyncio.sleep(0.01)
            return "test_result"

        result = run_coroutine_in_new_thread(test_coro())
        assert result == "test_result"

    @pytest.mark.asyncio
    async def test_run_coroutine_with_exception(self):
        """Test running coroutine that raises exception."""

        async def failing_coro():
            await asyncio.sleep(0.01)
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            run_coroutine_in_new_thread(failing_coro())


class TestGetCallerInfo:
    """Test get_caller_info function."""

    def test_get_caller_info(self):
        """Test getting caller info."""
        # Call from this function
        result = get_caller_info(1)

        # @safe decorator returns a Result type
        assert isinstance(result, Result)

        # The result should be Success since get_caller_info should work
        assert isinstance(result, Success)

        # Extract the values
        file_name, line_number = result.unwrap()

        # Should have file name and line number
        assert file_name is not None
        assert isinstance(line_number, int)
        assert line_number > 0

        # The file should be some python file (could be returns module due to decorator)
        assert file_name.endswith(".py")


class TestProvidableToInjected:
    """Test providable_to_injected function."""

    def test_with_injected(self):
        """Test with Injected instance."""
        injected = Injected.pure(42)
        result = providable_to_injected(injected)
        assert result is injected

    def test_with_callable(self):
        """Test with callable."""

        def test_func(a, b):
            return a + b

        result = providable_to_injected(test_func)
        assert isinstance(result, Injected)

    def test_with_string(self):
        """Test with string key."""
        result = providable_to_injected("test_key")
        assert isinstance(result, Injected)

    def test_with_invalid_type(self):
        """Test with invalid type."""
        with pytest.raises(Exception):
            providable_to_injected(123)  # Not a valid providable


class TestEventDistributor:
    """Test EventDistributor class."""

    def test_is_dataclass(self):
        """Test that EventDistributor is a dataclass."""
        assert is_dataclass(EventDistributor)

    def test_register_and_emit(self):
        """Test register callback and emit event."""
        callback1 = Mock()
        callback2 = Mock()
        distributor = EventDistributor()

        # Register callbacks
        distributor.register(callback1)
        distributor.register(callback2)

        # Emit event
        test_event = ProvideEvent(trace=["test"], kind="provide", data="value")
        distributor.emit(test_event)

        # Both callbacks should be called
        callback1.assert_called_once_with(test_event)
        callback2.assert_called_once_with(test_event)

    def test_unregister(self):
        """Test unregister callback."""
        callback = Mock()
        distributor = EventDistributor()

        distributor.register(callback)
        distributor.unregister(callback)

        # Emit event after unregister
        test_event = ProvideEvent(trace=["test"], kind="provide", data="value")
        distributor.emit(test_event)

        # Callback should not be called
        callback.assert_not_called()

    def test_event_history(self):
        """Test event history replay on new registration."""
        distributor = EventDistributor()

        # Emit some events
        event1 = ProvideEvent(trace=["test1"], kind="provide", data="value1")
        event2 = ProvideEvent(trace=["test2"], kind="provide", data="value2")
        distributor.emit(event1)
        distributor.emit(event2)

        # Register callback after events
        callback = Mock()
        distributor.register(callback)

        # Callback should be called with historical events
        assert callback.call_count == 2
        callback.assert_any_call(event1)
        callback.assert_any_call(event2)


class TestSessionValue:
    """Test SessionValue class."""

    def test_is_dataclass(self):
        """Test that SessionValue is a dataclass."""
        assert is_dataclass(SessionValue)

    def test_creation(self):
        """Test SessionValue creation."""
        parent = Mock(spec=IObjectGraph)
        session = Mock(spec=IObjectGraph)
        parent.child_session = Mock(return_value=session)

        designed = Mock()
        designed.design = Mock()

        value = SessionValue(parent=parent, designed=designed)

        assert value.parent is parent
        assert value.designed is designed
        assert value.session is session

        # Verify child_session was called
        parent.child_session.assert_called_once_with(designed.design)


class TestIObjectGraphSessioned:
    """Test IObjectGraph sessioned method pattern matching."""

    def test_sessioned_with_string(self):
        """Test sessioned method with string input - should recurse through Injected."""
        from pinjected.di.graph import MyObjectGraph
        from pinjected import design

        # Create graph with a test binding
        test_design = design(test_key="test_value")
        graph = MyObjectGraph.root(test_design)

        # Test string input - it should convert to Injected.by_name and then to Designed
        result = graph.sessioned("test_key")

        # Verify result is a DelegatedVar
        assert isinstance(result, DelegatedVar)

    def test_sessioned_with_injected(self):
        """Test sessioned method with Injected input - should convert to Designed."""
        from pinjected.di.graph import MyObjectGraph
        from pinjected import design

        # Create graph with test binding
        test_design = design(test_key="test_value")
        graph = MyObjectGraph.root(test_design)

        # Create an Injected instance
        injected = Injected.by_name("test_key")

        # Test with Injected - it should convert to Designed.bind(injected)
        result = graph.sessioned(injected)

        # Verify result is a DelegatedVar
        assert isinstance(result, DelegatedVar)

    def test_sessioned_with_callable(self):
        """Test sessioned method with callable input - should convert through Injected.bind."""
        from pinjected.di.graph import MyObjectGraph
        from pinjected import EmptyDesign

        # Create graph
        design = EmptyDesign
        graph = MyObjectGraph.root(design)

        # Create a callable
        def test_provider():
            return "test_value"

        # Test with callable - it should convert to Injected.bind(callable)
        result = graph.sessioned(test_provider)

        # Verify result is a DelegatedVar
        assert isinstance(result, DelegatedVar)

    def test_sessioned_with_designed(self):
        """Test sessioned method with Designed input - creates SessionValue."""
        from pinjected.di.graph import MyObjectGraph
        from pinjected import EmptyDesign

        # Create graph
        design = EmptyDesign
        graph = MyObjectGraph.root(design)

        # Create a Designed instance
        designed = Designed.bind(Injected.pure("test_value"))

        # Test with Designed - should create SessionValue and return DelegatedVar
        result = graph.sessioned(designed)

        # Verify result is a DelegatedVar
        assert isinstance(result, DelegatedVar)

        # The result should be a properly formed DelegatedVar

    def test_sessioned_pattern_matching_coverage(self):
        """Test sessioned method hits all pattern matching branches."""
        from pinjected.di.graph import MyObjectGraph
        from pinjected import design

        # Create graph with test bindings
        test_design = design(
            test_str="string_value", test_callable=lambda: "callable_value"
        )
        graph = MyObjectGraph.root(test_design)

        # Test 1: String input (case str())
        result1 = graph.sessioned("test_str")
        assert isinstance(result1, DelegatedVar)

        # Test 2: Injected input (case Injected())
        injected = Injected.by_name("test_str")
        result2 = graph.sessioned(injected)
        assert isinstance(result2, DelegatedVar)

        # Test 3: Callable input (case provider if callable(provider))
        def provider():
            return "provider_value"

        result3 = graph.sessioned(provider)
        assert isinstance(result3, DelegatedVar)

        # Test 4: Designed input (case Designed())
        designed = Designed.bind(Injected.pure("designed_value"))
        result4 = graph.sessioned(designed)
        assert isinstance(result4, DelegatedVar)

        # Note: DelegatedVar case is tricky because DelegatedVar is callable
        # and would match the callable case first

    def test_sessioned_with_unknown_type(self):
        """Test sessioned method with unknown type raises TypeError."""
        from pinjected.di.graph import MyObjectGraph
        from pinjected import EmptyDesign

        # Create graph
        design = EmptyDesign
        graph = MyObjectGraph.root(design)

        # Test with an unsupported type
        with pytest.raises(TypeError, match="Unknown target:.*queried for DI"):
            graph.sessioned(123)  # Integer is not a supported type


class TestMyObjectGraphProvidableToDesigned:
    """Test MyObjectGraph _providable_to_designed method pattern matching."""

    def test_providable_to_designed_with_string(self):
        """Test _providable_to_designed with string input - converts through Injected.by_name."""
        from pinjected.di.graph import MyObjectGraph
        from pinjected import EmptyDesign

        # Create graph
        design = EmptyDesign
        graph = MyObjectGraph.root(design)

        # Test with string - should convert to Injected.by_name then Designed.bind
        result = graph._providable_to_designed("test_key")

        # Verify result is Designed
        assert isinstance(result, Designed)

    def test_providable_to_designed_with_injected(self):
        """Test _providable_to_designed with Injected input - converts to Designed."""
        from pinjected.di.graph import MyObjectGraph
        from pinjected import EmptyDesign

        # Create graph
        design = EmptyDesign
        graph = MyObjectGraph.root(design)

        # Create an Injected instance
        injected = Injected.by_name("test")

        # Test with Injected - should convert to Designed.bind(injected)
        result = graph._providable_to_designed(injected)

        # Verify result is Designed
        assert isinstance(result, Designed)

    def test_providable_to_designed_with_designed(self):
        """Test _providable_to_designed with Designed input - returns as-is."""
        from pinjected.di.graph import MyObjectGraph
        from pinjected import EmptyDesign

        # Create graph
        design = EmptyDesign
        graph = MyObjectGraph.root(design)

        # Create a Designed instance
        designed = Designed.bind(Injected.pure("test"))

        # Test with Designed - should return the same object
        result = graph._providable_to_designed(designed)

        # Should return the same object
        assert result is designed

    def test_providable_to_designed_with_delegated_var(self):
        """Test _providable_to_designed with DelegatedVar input - evals and recurses."""
        from pinjected.di.graph import MyObjectGraph
        from pinjected import EmptyDesign

        # Create graph
        design = EmptyDesign
        graph = MyObjectGraph.root(design)

        # Create a DelegatedVar that evaluates to a Designed
        expected_designed = Designed.bind(Injected.pure("test"))
        delegated = Mock(spec=DelegatedVar)
        delegated.eval.return_value = expected_designed

        # Test with DelegatedVar - should eval and recurse
        result = graph._providable_to_designed(delegated)

        # Verify eval was called
        delegated.eval.assert_called_once()

        # Result should be the designed from eval
        assert isinstance(result, Designed)

    def test_providable_to_designed_with_callable(self):
        """Test _providable_to_designed with callable input - converts through Injected.bind."""
        from pinjected.di.graph import MyObjectGraph
        from pinjected import EmptyDesign

        # Create graph
        design = EmptyDesign
        graph = MyObjectGraph.root(design)

        def test_func():
            return "value"

        # Test with callable - should convert to Injected.bind then Designed.bind
        result = graph._providable_to_designed(test_func)

        # Verify result is Designed
        assert isinstance(result, Designed)

    def test_providable_to_designed_with_unknown_type(self):
        """Test _providable_to_designed with unknown type raises TypeError."""
        from pinjected.di.graph import MyObjectGraph
        from pinjected import EmptyDesign

        # Create graph
        design = EmptyDesign
        graph = MyObjectGraph.root(design)

        # Test with an unsupported type
        with pytest.raises(TypeError, match="Unknown target:.*queried for DI"):
            graph._providable_to_designed(123)  # Integer is not a supported type


class TestMyObjectGraphChildSession:
    """Test MyObjectGraph child_session method."""

    def test_child_session_without_overrides(self):
        """Test child_session method without overrides."""
        from pinjected.di.graph import MyObjectGraph
        from pinjected import EmptyDesign

        # Create a root graph
        design = EmptyDesign
        root_graph = MyObjectGraph.root(design)

        # Create child session without overrides
        child = root_graph.child_session()

        # Verify child was created properly
        assert isinstance(child, MyObjectGraph)
        assert isinstance(child.scope, MChildScope)
        assert child.scope.parent is root_graph.scope
        assert len(child.scope.override_targets) == 0

    def test_child_session_with_overrides(self):
        """Test child_session method with design overrides."""
        from pinjected.di.graph import MyObjectGraph
        from pinjected import design, EmptyDesign

        # Create a root graph
        root_design = EmptyDesign
        root_graph = MyObjectGraph.root(root_design)

        # Create overrides
        overrides = design(test_key="overridden_value")

        # Create child session with overrides
        child = root_graph.child_session(overrides)

        # Verify child was created properly
        assert isinstance(child, MyObjectGraph)
        assert isinstance(child.scope, MChildScope)
        assert child.scope.parent is root_graph.scope
        # The override_targets contains StrBindKey objects, not strings
        assert len(child.scope.override_targets) == 1
        # Check that a StrBindKey with name 'test_key' is in the set
        assert any(
            hasattr(key, "name") and key.name == "test_key"
            for key in child.scope.override_targets
        )

    def test_child_session_with_custom_trace_logger(self):
        """Test child_session method with custom trace logger."""
        from pinjected.di.graph import MyObjectGraph
        from pinjected import EmptyDesign

        # Create a root graph
        design = EmptyDesign
        root_graph = MyObjectGraph.root(design)

        # Create custom trace logger
        custom_logger = Mock()

        # Create child session with custom logger
        child = root_graph.child_session(trace_logger=custom_logger)

        # Verify logger was set
        assert child.scope._trace_logger is custom_logger

    def test_child_session_resolver_inheritance(self):
        """Test that child session inherits resolver properly."""
        from pinjected.di.graph import MyObjectGraph
        from pinjected import design

        # Create a root graph with some bindings
        root_design = design(parent_key="parent_value")
        root_graph = MyObjectGraph.root(root_design)

        # Create child with additional bindings
        child_overrides = design(child_key="child_value")
        child = root_graph.child_session(child_overrides)

        # Verify resolver was created properly
        assert child.resolver is not None
        assert child.resolver != root_graph.resolver
        # The child's design should include both parent and child bindings
        assert child.design == root_graph.design + child_overrides


class TestIObjectGraphAbstractMethods:
    """Test IObjectGraph abstract methods coverage."""

    def test_provide_abstract_method(self):
        """Test that provide is abstract and must be implemented."""

        # Create a class that doesn't implement provide
        class IncompleteGraph(IObjectGraph):
            def child_session(self, overrides=None):
                return self

        # Should not be able to instantiate
        with pytest.raises(
            TypeError, match="Can't instantiate abstract class.*provide"
        ):
            IncompleteGraph()

    def test_child_session_abstract_raises(self):
        """Test that child_session raises NotImplementedError in base class."""
        # The base IObjectGraph.child_session should raise NotImplementedError
        # This tests line 119 in graph.py
        mock_graph = Mock(spec=IObjectGraph)
        # Manually call the abstract method to test the NotImplementedError
        with pytest.raises(NotImplementedError):
            IObjectGraph.child_session(mock_graph)


class TestProvidableToInjected:
    """Test providable_to_injected function."""

    def test_providable_to_injected_with_string(self):
        """Test providable_to_injected with string input."""
        result = providable_to_injected("test_key")
        assert isinstance(result, InjectedByName)
        assert result.name == "test_key"

    def test_providable_to_injected_with_injected(self):
        """Test providable_to_injected with Injected input."""
        injected = Injected.by_name("test")
        result = providable_to_injected(injected)
        assert result is injected

    def test_providable_to_injected_with_callable(self):
        """Test providable_to_injected with callable input."""

        def test_func():
            return "value"

        result = providable_to_injected(test_func)
        assert isinstance(result, Injected)

    def test_providable_to_injected_with_class(self):
        """Test providable_to_injected with class input."""

        class TestClass:
            pass

        result = providable_to_injected(TestClass)
        assert isinstance(result, Injected)

    def test_providable_to_injected_with_invalid_type(self):
        """Test providable_to_injected with invalid type."""
        with pytest.raises(
            TypeError, match="target must be either class or a string or Injected"
        ):
            providable_to_injected(123)  # Integer is not supported


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
