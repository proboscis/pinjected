"""Simple tests to improve coverage for pinjected/di/graph.py."""

import pytest
from unittest.mock import Mock, patch
import asyncio
from returns.result import Result, Success, Failure

from pinjected.di.graph import (
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
    MyObjectGraph,
    DependencyResolver,
    DependencyResolutionError,
)
from pinjected.exceptions import DependencyResolutionFailure
from pinjected import Injected
from pinjected.di.designed import Designed
from pinjected.di.injected import InjectedByName


class TestBasicGraphComponents:
    """Test basic graph components."""

    def test_trace_string_empty(self):
        """Test trace_string with empty list."""
        assert trace_string([]) == ""

    def test_trace_string_single(self):
        """Test trace_string with single item."""
        assert trace_string(["item"]) == "item"

    def test_trace_string_multiple(self):
        """Test trace_string with multiple items."""
        assert trace_string(["a", "b", "c"]) == "a -> b -> c"

    def test_no_mapping_error_creation(self):
        """Test NoMappingError creation."""
        error = NoMappingError("test_key")
        assert str(error) == "No mapping found for DI:test_key"
        assert error.key == "test_key"

    def test_provide_event_creation(self):
        """Test ProvideEvent creation."""
        event = ProvideEvent(trace=["key1", "key2"], kind="request")
        assert event.trace == ["key1", "key2"]
        assert event.kind == "request"
        assert event.data is None

        event2 = ProvideEvent(trace=["key"], kind="provide", data="result")
        assert event2.data == "result"

    def test_event_distributor(self):
        """Test EventDistributor functionality."""
        dist = EventDistributor()
        assert dist.callbacks == []
        assert dist.event_history == []

        # Add callbacks
        callback1 = Mock()
        callback2 = Mock()
        dist.register(callback1)
        dist.register(callback2)

        # Emit event
        event = ProvideEvent(["key"], "provide", "data")
        dist.emit(event)

        callback1.assert_called_once_with(event)
        callback2.assert_called_once_with(event)
        assert event in dist.event_history

    def test_get_caller_info(self):
        """Test get_caller_info returns valid info."""
        result = get_caller_info(1)

        # @safe decorator returns a Result type
        assert isinstance(result, Result)
        assert isinstance(result, Success)

        # Extract the values
        filename, lineno = result.unwrap()
        assert isinstance(filename, str)
        assert isinstance(lineno, int)
        assert lineno > 0

    def test_providable_to_injected_string(self):
        """Test providable_to_injected with string."""
        result = providable_to_injected("test_key")
        assert isinstance(result, InjectedByName)
        assert result.name == "test_key"

    def test_providable_to_injected_injected(self):
        """Test providable_to_injected with Injected."""
        injected = InjectedByName("test")
        result = providable_to_injected(injected)
        assert result is injected

    def test_providable_to_injected_callable(self):
        """Test providable_to_injected with callable."""

        def test_func():
            return "value"

        result = providable_to_injected(test_func)
        assert isinstance(result, Injected)

    def test_providable_to_injected_invalid(self):
        """Test providable_to_injected with invalid type."""
        with pytest.raises(
            TypeError, match="target must be either class or a string or Injected"
        ):
            providable_to_injected(123)


class TestMScope:
    """Test MScope implementation."""

    def test_init_default(self):
        """Test MScope default initialization."""
        scope = MScope()
        assert scope.cache == {}
        assert scope._trace_logger is not None
        assert scope.trace_logger == scope._trace_logger

    def test_init_custom_logger(self):
        """Test MScope with custom trace logger."""
        custom_logger = Mock()
        scope = MScope(_trace_logger=custom_logger)
        assert scope.trace_logger == custom_logger

    def test_contains(self):
        """Test __contains__ method."""
        scope = MScope()
        scope.cache["exists"] = "value"

        assert "exists" in scope
        assert "not_exists" not in scope

    def test_provide_cached(self):
        """Test provide returns cached value."""
        scope = MScope()
        scope._trace_logger = Mock()
        scope.cache["key"] = "cached_value"

        provider = Mock()
        result = scope.provide("key", provider, ["key"])

        assert result == "cached_value"
        provider.assert_not_called()

        # Check trace logger was called twice (request and provide)
        assert scope._trace_logger.call_count == 2

    def test_provide_not_cached(self):
        """Test provide computes new value."""
        scope = MScope()
        scope._trace_logger = Mock()

        provider = Mock(return_value="new_value")
        result = scope.provide("key", provider, ["parent", "key"])

        assert result == "new_value"
        assert scope.cache["key"] == "new_value"
        provider.assert_called_once()

    def test_provide_invalid_trace(self):
        """Test provide validates trace."""
        scope = MScope()

        # Last element doesn't match key
        with pytest.raises(AssertionError):
            scope.provide("key", Mock(), ["parent", "wrong_key"])

    def test_getstate_not_serializable(self):
        """Test MScope cannot be serialized."""
        scope = MScope()
        with pytest.raises(NotImplementedError, match="not serializable"):
            scope.__getstate__()


class TestMChildScope:
    """Test MChildScope implementation."""

    def test_init(self):
        """Test MChildScope initialization."""
        parent = Mock(spec=IScope)
        overrides = {"key1", "key2"}
        child = MChildScope(parent=parent, override_targets=overrides)

        assert child.parent is parent
        assert child.override_targets == overrides
        assert child.cache == {}

    def test_provide_override(self):
        """Test provide with override target."""
        parent = Mock(spec=IScope)
        child = MChildScope(parent=parent, override_targets={"override_key"})
        child._trace_logger = Mock()

        provider = Mock(return_value="override_value")
        result = child.provide("override_key", provider, ["override_key"])

        assert result == "override_value"
        assert child.cache["override_key"] == "override_value"
        parent.provide.assert_not_called()

    def test_provide_from_parent(self):
        """Test provide delegates to parent."""
        parent = Mock(spec=IScope)
        parent.provide.return_value = "parent_value"
        parent.__contains__ = Mock(return_value=True)  # normal_key is in parent

        child = MChildScope(parent=parent, override_targets={"other_key"})

        provider = Mock()
        result = child.provide("normal_key", provider, ["normal_key"])

        assert result == "parent_value"
        parent.provide.assert_called_once_with("normal_key", provider, ["normal_key"])

    def test_contains(self):
        """Test __contains__ checks both scopes."""
        parent = Mock(spec=IScope)
        parent.__contains__ = Mock(side_effect=lambda k: k == "parent_key")

        child = MChildScope(parent=parent, override_targets=set())
        child.cache["child_key"] = "value"

        assert "child_key" in child
        assert "parent_key" in child
        assert "missing_key" not in child


class TestOverridingScope:
    """Test OverridingScope implementation."""

    def test_provide_with_override(self):
        """Test provide uses override value."""
        parent = Mock(spec=IScope)
        overrides = {"key1": "override1", "key2": "override2"}
        scope = OverridingScope(src=parent, overrides=overrides)

        provider = Mock()
        result = scope.provide("key1", provider, ["key1"])

        assert result == "override1"
        provider.assert_not_called()
        parent.provide.assert_not_called()

    def test_provide_without_override(self):
        """Test provide delegates to parent."""
        parent = Mock(spec=IScope)
        parent.provide.return_value = "parent_value"

        scope = OverridingScope(src=parent, overrides={"other": "value"})

        provider = Mock()
        result = scope.provide("key", provider, ["key"])

        assert result == "parent_value"
        parent.provide.assert_called_once()

    def test_trace_logger_property(self):
        """Test trace_logger delegates to parent."""
        parent = Mock(spec=IScope)
        logger = Mock()
        parent.trace_logger = logger

        scope = OverridingScope(src=parent, overrides={})
        assert scope.trace_logger == logger


class TestSessionValue:
    """Test SessionValue class."""

    def test_init(self):
        """Test SessionValue initialization."""
        graph = Mock(spec=IObjectGraph)
        designed = Mock(spec=Designed)

        session = SessionValue(graph, designed)

        assert session.parent is graph
        assert session.designed is designed

    def test_get(self):
        """Test SessionValue.get() method."""
        graph = Mock(spec=IObjectGraph)

        # Set up designed mock
        designed = Mock(spec=Designed)
        designed.design = Mock()
        designed.internal_injected = "test_injected"

        # Set up child_session mock
        child_session = Mock()
        child_session.__getitem__ = Mock(return_value="provided_value")
        graph.child_session.return_value = child_session

        session = SessionValue(graph, designed)
        result = session.value

        assert result == "provided_value"
        child_session.__getitem__.assert_called_once_with("test_injected")

    def test_await(self):
        """Test SessionValue value property access."""
        # SessionValue doesn't have __await__ method
        # Testing value property instead
        graph = Mock(spec=IObjectGraph)

        # Set up designed mock
        designed = Mock(spec=Designed)
        designed.design = Mock()
        designed.internal_injected = "test_injected"

        # Set up child_session mock
        child_session = Mock()
        child_session.__getitem__ = Mock(return_value="async_value")
        graph.child_session.return_value = child_session

        session = SessionValue(graph, designed)

        # Test both value and __value__ properties
        assert session.value == "async_value"
        assert session.__value__ == "async_value"


class TestRichTraceLogger:
    """Test RichTraceLogger class."""

    def test_request_event(self):
        """Test logging request event."""
        mock_console = Mock()
        logger = RichTraceLogger(console=mock_console)

        event = ProvideEvent(["a", "b", "c"], "request")
        logger(event)

        # Should log twice for request
        assert mock_console.log.call_count == 2
        mock_console.log.assert_any_call("provide trace:['a', 'b', 'c']")

    def test_provide_event(self):
        """Test logging provide event."""
        mock_console = Mock()
        logger = RichTraceLogger(console=mock_console)

        with patch("pinjected.di.graph.Panel") as mock_panel:
            event = ProvideEvent(["key"], "provide", data="result")
            logger(event)

            # Should create panels
            assert mock_panel.call_count == 2


class TestAsyncFunctions:
    """Test async-related functions."""

    def test_run_coroutine_in_new_thread(self):
        """Test running coroutine in new thread."""

        async def test_coro():
            await asyncio.sleep(0.01)
            return "async_result"

        result = run_coroutine_in_new_thread(test_coro())
        assert result == "async_result"

    def test_run_coroutine_with_exception(self):
        """Test coroutine exception propagation."""

        async def failing_coro():
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            run_coroutine_in_new_thread(failing_coro())


class TestMyObjectGraph:
    """Test MyObjectGraph basic functionality."""

    def test_properties(self):
        """Test MyObjectGraph properties."""
        design = Mock()
        resolver = Mock(spec=DependencyResolver)
        scope = Mock(spec=IScope)

        graph = MyObjectGraph(_resolver=resolver, src_design=design, scope=scope)

        # Check factory is created from design
        assert hasattr(graph, "factory")
        assert graph.src_design is design
        assert graph.resolver is resolver
        assert graph.scope is scope

    def test_provide_success(self):
        """Test successful provide."""
        resolver = Mock(spec=DependencyResolver)

        # Set up dependency_tree to return a Success with empty dict
        resolver.dependency_tree.return_value = Success({})
        # Set up find_failures to return empty dict (no failures)
        resolver.find_failures.return_value = {}
        # Set up provide to return Success
        resolver.provide.return_value = Success("result")

        # Mock the design properly
        design_mock = Mock()
        design_mock.bindings = {}  # DIGraph expects this to be iterable

        graph = MyObjectGraph(_resolver=resolver, src_design=design_mock, scope=Mock())

        result = graph.provide("test_key")
        # provide returns a Result object
        assert isinstance(result, Success)
        assert result.unwrap() == "result"

    def test_provide_failure(self):
        """Test provide with failure."""
        failure = Mock(spec=DependencyResolutionFailure)
        resolver = Mock(spec=DependencyResolver)

        # Set up dependency_tree to return a Success with nested Result values
        resolver.dependency_tree.return_value = Success({"test": Failure(failure)})
        # Set up find_failures to return failures (list, not dict)
        resolver.find_failures.return_value = [failure]

        # Mock the design properly
        design_mock = Mock()
        design_mock.bindings = {}

        graph = MyObjectGraph(_resolver=resolver, src_design=design_mock, scope=Mock())

        with pytest.raises(DependencyResolutionError):
            graph.provide("test_key")


class TestOGFactoryByDesign:
    """Test OGFactoryByDesign class."""

    def test_create(self):
        """Test create method."""
        mock_design = Mock()
        mock_graph = Mock(spec=IObjectGraph)
        mock_design.to_graph.return_value = mock_graph

        factory = OGFactoryByDesign(src=mock_design)
        result = factory.create()

        assert result is mock_graph
        mock_design.to_graph.assert_called_once()


class TestIScope:
    """Test IScope default trace logger."""

    def test_default_trace_logger_request(self):
        """Test logging request events."""
        with patch("pinjected.pinjected_logging.logger") as mock_logger:
            event = ProvideEvent(["a", "b", "c"], "request")
            IScope.default_trace_logger(event)

            mock_logger.info.assert_called_once_with("a -> b -> c")

    def test_default_trace_logger_large_list(self):
        """Test logging large list results."""
        with patch("pinjected.pinjected_logging.logger") as mock_logger:
            large_list = list(range(150))
            event = ProvideEvent(["key"], "provide", data=large_list)
            IScope.default_trace_logger(event)

            call_args = mock_logger.info.call_args[0][0]
            assert "LARGE LIST(150 items)" in call_args

    def test_default_trace_logger_small_list(self):
        """Test logging small list results."""
        with patch("pinjected.pinjected_logging.logger") as mock_logger:
            event = ProvideEvent(["key"], "provide", data=[1, 2, 3])
            IScope.default_trace_logger(event)

            call_args = mock_logger.info.call_args[0][0]
            assert "[1, 2, 3]" in call_args

    def test_default_trace_logger_exception(self):
        """Test handling logging exceptions."""
        with patch("pinjected.pinjected_logging.logger") as mock_logger:
            # Create object that raises on str()
            class BadStr:
                def __str__(self):
                    raise ValueError("Cannot stringify")

            event = ProvideEvent(["key"], "provide", data=BadStr())
            IScope.default_trace_logger(event)

            mock_logger.error.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
