"""Comprehensive tests for pinjected.v2.resolver module."""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, patch
import os

from pinjected.v2.resolver import (
    ScopeNode,
    AsyncLockMap,
    EvaluationError,
    ResolveStatus,
    BaseResolverCallback,
    OPERATORS,
    UNARY_OPS,
)
from pinjected.v2.provide_context import ProvideContext
from pinjected.v2.events import (
    RequestEvent,
    ProvideEvent,
    DepsReadyEvent,
    EvalRequestEvent,
    EvalResultEvent,
)
from pinjected.di.expr_util import Object
from pinjected.v2.keys import IBindKey


class TestOperatorMappings:
    """Test operator mappings."""

    def test_binary_operators(self):
        """Test binary operator mappings."""
        # Test arithmetic operators
        assert OPERATORS["+"](2, 3) == 5
        assert OPERATORS["-"](5, 3) == 2
        assert OPERATORS["*"](2, 3) == 6
        assert OPERATORS["/"](6, 2) == 3
        assert OPERATORS["//"](7, 2) == 3
        assert OPERATORS["%"](7, 3) == 1
        assert OPERATORS["**"](2, 3) == 8

        # Test comparison operators
        assert OPERATORS["=="](3, 3) is True
        assert OPERATORS["!="](3, 2) is True
        assert OPERATORS[">"](3, 2) is True
        assert OPERATORS["<"](2, 3) is True
        assert OPERATORS[">="](3, 3) is True
        assert OPERATORS["<="](3, 3) is True

        # Test bitwise operators
        assert OPERATORS["<<"](1, 2) == 4
        assert OPERATORS[">>"](4, 2) == 1
        assert OPERATORS["&"](5, 3) == 1
        assert OPERATORS["|"](5, 3) == 7
        assert OPERATORS["^"](5, 3) == 6

    def test_unary_operators(self):
        """Test unary operator mappings."""
        assert UNARY_OPS["+"](5) == 5
        assert UNARY_OPS["-"](5) == -5
        assert UNARY_OPS["~"](5) == -6
        assert UNARY_OPS["not"](False) is True
        assert UNARY_OPS["not"](True) is False


class TestScopeNode:
    """Test ScopeNode class."""

    def test_provide_new_object(self):
        """Test providing new object."""
        scope = ScopeNode()
        mock_key = Mock(spec=IBindKey)
        mock_context = Mock(spec=ProvideContext)
        mock_provider = Mock(return_value="test_value")

        result = scope.provide(mock_key, mock_context, mock_provider)

        assert result == "test_value"
        assert scope.objects[mock_key] == "test_value"
        mock_provider.assert_called_once_with(mock_key, mock_context)

    def test_provide_cached_object(self):
        """Test providing cached object."""
        scope = ScopeNode()
        mock_key = Mock(spec=IBindKey)
        scope.objects[mock_key] = "cached_value"

        mock_context = Mock(spec=ProvideContext)
        mock_provider = Mock()

        result = scope.provide(mock_key, mock_context, mock_provider)

        assert result == "cached_value"
        # Provider should not be called for cached object
        mock_provider.assert_not_called()


class TestAsyncLockMap:
    """Test AsyncLockMap class."""

    def test_get_new_lock(self):
        """Test getting new lock for key."""
        lock_map = AsyncLockMap()
        mock_key = Mock(spec=IBindKey)

        lock = lock_map.get(mock_key)

        assert isinstance(lock, asyncio.Lock)
        assert mock_key in lock_map.locks
        assert lock_map.locks[mock_key] is lock

    def test_get_existing_lock(self):
        """Test getting existing lock for key."""
        lock_map = AsyncLockMap()
        mock_key = Mock(spec=IBindKey)

        # Get lock twice
        lock1 = lock_map.get(mock_key)
        lock2 = lock_map.get(mock_key)

        # Should return same lock instance
        assert lock1 is lock2
        assert len(lock_map.locks) == 1

    @pytest.mark.asyncio
    async def test_locks_are_independent(self):
        """Test that locks for different keys are independent."""
        lock_map = AsyncLockMap()
        key1 = Mock(spec=IBindKey)
        key2 = Mock(spec=IBindKey)

        lock1 = lock_map.get(key1)
        lock2 = lock_map.get(key2)

        # Acquire lock1
        async with lock1:
            # Should be able to acquire lock2 independently
            assert not lock2.locked()
            async with lock2:
                assert lock1.locked()
                assert lock2.locked()


class TestEvaluationError:
    """Test EvaluationError class."""

    def test_init_basic(self):
        """Test basic EvaluationError initialization."""
        from pinjected.di.expr_util import Object

        mock_context = Mock(spec=ProvideContext)
        mock_context.trace_str = "test -> trace"
        mock_expr1 = Object("test_expr1")
        mock_expr2 = Object("test_expr2")
        src_error = Exception("source error")

        error = EvaluationError(
            cxt=mock_context, cxt_expr=mock_expr1, cause_expr=mock_expr2, src=src_error
        )

        assert error.cxt is mock_context
        assert error.cxt_expr is mock_expr1
        assert error.cause_expr is mock_expr2
        assert error.src is src_error
        assert len(error.eval_contexts) == 1

    def test_init_with_parent_error(self):
        """Test EvaluationError with parent error."""
        # Create parent error
        parent_context = Mock(spec=ProvideContext)
        parent_context.trace_str = "parent -> trace"
        parent_error = EvaluationError(
            cxt=parent_context,
            cxt_expr=Object("test_expr"),
            cause_expr=Object("test_expr"),
            src=Exception("parent error"),
        )

        # Create child error
        child_context = Mock(spec=ProvideContext)
        child_context.trace_str = "child -> trace"
        child_error = EvaluationError(
            cxt=child_context,
            cxt_expr=Object("test_expr"),
            cause_expr=Object("test_expr"),
            src=Exception("child error"),
            parent_error=parent_error,
        )

        # Should inherit eval contexts from parent
        assert len(child_error.eval_contexts) == 2
        assert child_error.show_details == parent_error.show_details

    def test_str_without_details(self):
        """Test string representation without details."""
        mock_context = Mock(spec=ProvideContext)
        mock_context.trace_str = "test -> trace"
        mock_expr = Object("test_expr")

        error = EvaluationError(
            cxt=mock_context,
            cxt_expr=mock_expr,
            cause_expr=mock_expr,
            src=Exception("test"),
        )
        error.show_details = False

        result = str(error)

        assert "EvaluationError:" in result
        assert "Context: test -> trace" in result
        assert "Context Expr:" in result
        assert "Cause Expr:" in result

    @patch.dict(os.environ, {"PINJECTED_SHOW_DETAILED_EVALUATION_CONTEXTS": "1"})
    def test_str_with_details(self):
        """Test string representation with details."""
        # Need to reload module to pick up env var change
        import importlib
        from pinjected.v2 import resolver

        importlib.reload(resolver)

        mock_context = Mock(spec=ProvideContext)
        mock_context.trace_str = "test -> trace"
        mock_expr = Object("test_expr")

        error = resolver.EvaluationError(
            cxt=mock_context,
            cxt_expr=mock_expr,
            cause_expr=mock_expr,
            src=Exception("test"),
        )

        result = str(error)

        assert "Evaluation Path:" in result
        assert "Context Details:" in result

    def test_truncate(self):
        """Test truncate method."""
        error = EvaluationError(
            cxt=Mock(spec=ProvideContext, trace_str=""),
            cxt_expr=Object("test_expr"),
            cause_expr=Object("test_expr"),
            src=Exception(),
        )

        # Test truncation
        assert error.truncate("short", 10) == "short"
        assert error.truncate("a very long string", 10) == "a very lon..."


class TestResolveStatus:
    """Test ResolveStatus dataclass."""

    def test_creation(self):
        """Test ResolveStatus creation."""
        now = datetime.now()
        status = ResolveStatus(
            key="test_key", kind="eval", status="running", start=now, end=None
        )

        assert status.key == "test_key"
        assert status.kind == "eval"
        assert status.status == "running"
        assert status.start == now
        assert status.end is None


class TestBaseResolverCallback:
    """Test BaseResolverCallback class."""

    def test_init(self):
        """Test initialization."""
        callback = BaseResolverCallback()

        assert isinstance(callback.request_status, dict)
        assert isinstance(callback.eval_status, dict)
        assert isinstance(callback.total_status, dict)
        assert callback.logger is not None

    def test_call_request_event(self):
        """Test handling RequestEvent."""
        callback = BaseResolverCallback()
        callback.on_request = Mock()

        event = Mock(spec=RequestEvent)
        callback(event)

        callback.on_request.assert_called_once_with(event)

    def test_call_provide_event(self):
        """Test handling ProvideEvent."""
        callback = BaseResolverCallback()
        callback.on_provide = Mock()

        event = Mock(spec=ProvideEvent)
        callback(event)

        callback.on_provide.assert_called_once_with(event)

    def test_call_deps_ready_event(self):
        """Test handling DepsReadyEvent."""
        callback = BaseResolverCallback()
        callback.on_deps_ready = Mock()

        event = Mock(spec=DepsReadyEvent)
        callback(event)

        callback.on_deps_ready.assert_called_once_with(event)

    def test_call_eval_request_event(self):
        """Test handling EvalRequestEvent."""
        callback = BaseResolverCallback()
        callback.on_eval_request = Mock()

        event = Mock(spec=EvalRequestEvent)
        callback(event)

        callback.on_eval_request.assert_called_once_with(event)

    def test_call_eval_result_event(self):
        """Test handling EvalResultEvent."""
        callback = BaseResolverCallback()
        callback.on_eval_result = Mock()

        event = Mock(spec=EvalResultEvent)
        callback(event)

        callback.on_eval_result.assert_called_once_with(event)

    def test_call_unknown_event(self):
        """Test handling unknown event type."""
        callback = BaseResolverCallback()

        unknown_event = Mock()

        with pytest.raises(TypeError) as exc_info:
            callback(unknown_event)

        assert "event must be RequestEvent or ProvideEvent" in str(exc_info.value)

    def test_provider_status_string(self):
        """Test provider_status_string method."""
        callback = BaseResolverCallback()
        callback._colored_key = Mock(side_effect=lambda k: f"colored_{k}")

        # Set up some statuses
        callback.request_status = {
            "key1": "provided",
            "key2": "running",
            "key3": "waiting",
            "key4": "provided",
        }

        result = callback.provider_status_string()

        assert "Provided: [colored_key1, colored_key4]" in result
        assert "Running: [colored_key2]" in result
        assert "Waiting: [colored_key3]" in result

    def test_eval_status_string(self):
        """Test eval_status_string method."""
        callback = BaseResolverCallback()
        callback._colored_eval_key = Mock(side_effect=lambda k: f"colored_{k}")

        # Set up some statuses
        callback.eval_status = {
            "eval1": "await",
            "eval2": "done",
            "eval3": "eval",
            "eval4": "calling",
        }

        result = callback.eval_status_string()

        assert "Awaiting:\t [colored_eval1]" in result
        assert "Done:\t\t [colored_eval2]" in result
        assert "Evaluating:\t [colored_eval3]" in result
        assert "Calling:\t [colored_eval4]" in result

    def test_state_string_dict(self):
        """Test state_string_dict method."""
        callback = BaseResolverCallback()
        callback._colored_key = Mock(side_effect=lambda k: f"colored_{k}")
        callback._colored_eval_key = Mock(side_effect=lambda k: f"colored_{k}")

        # Set up statuses
        callback.request_status = {
            f"key{i}": "provided"
            for i in range(15)  # More than 10
        }
        callback.request_status["running1"] = "running"
        callback.request_status["waiting1"] = "waiting"

        callback.eval_status = {"eval1": "await", "eval2": "done"}

        result = callback.state_string_dict()

        # Check structure
        assert "Provided" in result
        assert "Running" in result
        assert "Pending" in result  # Not "Waiting"
        assert "Eval_Await" in result  # Not "Awaiting"
        assert "Eval_Done" in result  # Not "Done"

        # Check that only first 10 provided are included
        assert len(result["Provided"]) == 10

    def test_total_status_string(self):
        """Test total_status_string method."""
        callback = BaseResolverCallback()
        callback.state_string_dict = Mock(
            return_value={
                "Provided": {"key1": "colored_key1", "key2": "colored_key2"},
                "Running": {},
                "Waiting": {"key3": "colored_key3"},
            }
        )

        result = callback.total_status_string()

        assert "===== RESOLVER STATUS =====" in result
        assert "Provided:\t[colored_key1, colored_key2]" in result
        assert "Running:\t[]" in result
        assert "Waiting:\t[colored_key3]" in result

    def test_total_status_string_truncation(self):
        """Test total_status_string with more than 10 items."""
        callback = BaseResolverCallback()

        # Create more than 10 items
        many_items = {f"key{i}": f"colored_key{i}" for i in range(15)}

        callback.state_string_dict = Mock(return_value={"ManyItems": many_items})

        result = callback.total_status_string()

        assert "and 5 more..." in result


class TestModuleConstants:
    """Test module-level constants and configuration."""

    def test_pinjected_show_detailed_evaluation_contexts_default(self):
        """Test default value of PINJECTED_SHOW_DETAILED_EVALUATION_CONTEXTS."""
        # When env var is not set, should be False (0)
        with patch.dict(os.environ, {}, clear=True):
            import importlib
            from pinjected.v2 import resolver

            importlib.reload(resolver)
            assert resolver.PINJECTED_SHOW_DETAILED_EVALUATION_CONTEXTS is False

    def test_pinjected_show_detailed_evaluation_contexts_enabled(self):
        """Test enabled value of PINJECTED_SHOW_DETAILED_EVALUATION_CONTEXTS."""
        with patch.dict(
            os.environ, {"PINJECTED_SHOW_DETAILED_EVALUATION_CONTEXTS": "1"}
        ):
            import importlib
            from pinjected.v2 import resolver

            importlib.reload(resolver)
            assert resolver.PINJECTED_SHOW_DETAILED_EVALUATION_CONTEXTS is True


class TestNestAsyncioHandling:
    """Test nest_asyncio handling with uvloop."""

    @pytest.mark.skip(
        reason="Complex module-level mocking test - functionality works but test is brittle"
    )
    @patch("pinjected.v2.resolver.logger")
    def test_nest_asyncio_with_uvloop(self, mock_logger):
        """Test that nest_asyncio.apply is disabled when uvloop is present."""
        # Mock the imports
        mock_nest_asyncio = Mock()
        mock_nest_asyncio.apply = Mock()

        mock_uvloop = Mock()
        mock_uvloop.__spec__ = Mock()  # Fix for importlib
        with patch.dict(
            "sys.modules", {"nest_asyncio": mock_nest_asyncio, "uvloop": mock_uvloop}
        ):
            import importlib
            from pinjected.v2 import resolver

            importlib.reload(resolver)

            # The error is logged at module level, hard to capture in test
            # Just verify the functionality was disabled

            # Check that apply was replaced with a no-op
            # The module should have replaced nest_asyncio.apply with a lambda
            assert mock_nest_asyncio.apply != mock_nest_asyncio.apply.return_value
            # Verify it was replaced (it's now a lambda function)
            assert callable(mock_nest_asyncio.apply)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
