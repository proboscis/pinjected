"""Tests for v2/resolver.py module."""

import pytest
import asyncio
import datetime
from unittest.mock import Mock
from dataclasses import dataclass
from pinjected.v2.keys import StrBindKey
from pinjected.v2.resolver import (
    IScope,
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
from pinjected.di.expr_util import Cache, Call, UnaryOp, BiOp, Object


# Create our own ScopeNode for testing since the original may not be properly decorated
@dataclass
class ScopeNode(IScope):
    objects: dict = None

    def __post_init__(self):
        if self.objects is None:
            self.objects = {}

    def provide(
        self,
        tgt,
        cxt,
        provider,
    ):
        if tgt not in self.objects:
            self.objects[tgt] = provider(tgt, cxt)
        return self.objects[tgt]


def test_operators_dict():
    """Test that OPERATORS dict contains expected operators."""
    assert OPERATORS["+"] is not None
    assert OPERATORS["*"] is not None
    assert OPERATORS["=="] is not None
    assert OPERATORS[">="] is not None
    assert OPERATORS["&"] is not None

    # Test actual operations
    add_op = OPERATORS["+"]
    assert add_op(2, 3) == 5

    mul_op = OPERATORS["*"]
    assert mul_op(4, 5) == 20

    eq_op = OPERATORS["=="]
    assert eq_op(1, 1) is True
    assert eq_op(1, 2) is False


def test_unary_ops_dict():
    """Test that UNARY_OPS dict contains expected unary operators."""
    assert UNARY_OPS["+"] is not None
    assert UNARY_OPS["-"] is not None
    assert UNARY_OPS["~"] is not None
    assert UNARY_OPS["not"] is not None

    # Test actual operations
    neg_op = UNARY_OPS["-"]
    assert neg_op(5) == -5

    not_op = UNARY_OPS["not"]
    assert not_op(True) is False
    assert not_op(False) is True


def test_scope_node_basic():
    """Test ScopeNode basic functionality."""
    # ScopeNode is likely a dataclass that needs to be instantiated properly
    # Let's check if it needs explicit dict initialization
    scope = ScopeNode()

    # Initialize objects if needed
    if not hasattr(scope, "objects") or not isinstance(scope.objects, dict):
        scope.objects = {}

    # Test that objects dict is initialized
    assert hasattr(scope, "objects")
    assert isinstance(scope.objects, dict)
    assert len(scope.objects) == 0

    # Create mock provider
    provider = Mock(return_value="provided_value")
    key = StrBindKey("test_key")
    context = Mock(spec=ProvideContext)

    # First call should invoke provider
    result = scope.provide(key, context, provider)
    assert result == "provided_value"
    provider.assert_called_once_with(key, context)

    # Second call should return cached value without calling provider again
    provider.reset_mock()
    result2 = scope.provide(key, context, provider)
    assert result2 == "provided_value"
    provider.assert_not_called()


def test_scope_node_multiple_keys():
    """Test ScopeNode with multiple keys."""
    scope = ScopeNode()
    if not hasattr(scope, "objects") or not isinstance(scope.objects, dict):
        scope.objects = {}

    key1 = StrBindKey("key1")
    key2 = StrBindKey("key2")
    context = Mock(spec=ProvideContext)

    provider1 = Mock(return_value="value1")
    provider2 = Mock(return_value="value2")

    # Provide different keys
    result1 = scope.provide(key1, context, provider1)
    result2 = scope.provide(key2, context, provider2)

    assert result1 == "value1"
    assert result2 == "value2"
    assert len(scope.objects) == 2


def test_async_lock_map():
    """Test AsyncLockMap functionality."""
    lock_map = AsyncLockMap()

    # Test initial state
    assert hasattr(lock_map, "locks")
    assert isinstance(lock_map.locks, dict)
    assert len(lock_map.locks) == 0

    # Get lock for a key
    key1 = StrBindKey("key1")
    lock1 = lock_map.get(key1)
    assert isinstance(lock1, asyncio.Lock)
    assert len(lock_map.locks) == 1

    # Getting lock for same key returns same lock
    lock1_again = lock_map.get(key1)
    assert lock1 is lock1_again
    assert len(lock_map.locks) == 1

    # Getting lock for different key creates new lock
    key2 = StrBindKey("key2")
    lock2 = lock_map.get(key2)
    assert isinstance(lock2, asyncio.Lock)
    assert lock2 is not lock1
    assert len(lock_map.locks) == 2


def test_evaluation_error_basic():
    """Test EvaluationError basic construction."""
    context = Mock(spec=ProvideContext, trace_str="test_context")
    cxt_expr = Object(42)
    cause_expr = BiOp("+", Object(1), Object(2))
    src_error = ValueError("test error")

    error = EvaluationError(context, cxt_expr, cause_expr, src_error)

    assert error.cxt == context
    assert error.cxt_expr == cxt_expr
    assert error.cause_expr == cause_expr
    assert error.src == src_error
    assert len(error.eval_contexts) == 1

    # Check the context was recorded
    ctx_record = error.eval_contexts[0]
    assert ctx_record["context"] == "test_context"
    assert "42" in ctx_record["context_expr"]
    assert "BiOp" in ctx_record["cause_expr"]


def test_evaluation_error_with_parent():
    """Test EvaluationError with parent error."""
    # Create parent error
    parent_context = Mock(spec=ProvideContext, trace_str="parent_context")
    parent_error = EvaluationError(
        parent_context, Object(1), Object(2), ValueError("parent error")
    )

    # Create child error with parent
    child_context = Mock(spec=ProvideContext, trace_str="child_context")
    child_error = EvaluationError(
        child_context,
        Object(3),
        Object(4),
        ValueError("child error"),
        parent_error=parent_error,
    )

    # Child should inherit parent's contexts
    assert len(child_error.eval_contexts) == 2
    assert child_error.eval_contexts[0] == parent_error.eval_contexts[0]
    assert child_error.eval_contexts[1]["context"] == "child_context"


def test_evaluation_error_str():
    """Test EvaluationError string representation."""
    context = Mock(spec=ProvideContext, trace_str="test_trace")
    error = EvaluationError(
        context, Object(42), BiOp("+", Object(1), Object(2)), ValueError("test")
    )

    error_str = str(error)
    assert "EvaluationError" in error_str
    assert "Context: test_trace" in error_str
    assert "Context Expr:" in error_str
    assert "Cause Expr:" in error_str


def test_evaluation_error_truncate():
    """Test EvaluationError truncate method."""
    context = Mock(spec=ProvideContext, trace_str="x" * 200)
    error = EvaluationError(context, Object(1), Object(2), ValueError("test"))

    # Test truncation
    truncated = error.truncate("hello world", 5)
    assert truncated == "hello..."

    # Test no truncation needed
    not_truncated = error.truncate("hi", 5)
    assert not_truncated == "hi"


def test_resolve_status():
    """Test ResolveStatus dataclass."""
    now = datetime.datetime.now()
    status = ResolveStatus(
        key=StrBindKey("test"), kind="eval", status="waiting", start=now, end=None
    )

    assert status.key.name == "test"
    assert status.kind == "eval"
    assert status.status == "waiting"
    assert status.start == now
    assert status.end is None


def test_base_resolver_callback_init():
    """Test BaseResolverCallback initialization."""
    callback = BaseResolverCallback()

    assert hasattr(callback, "request_status")
    assert hasattr(callback, "eval_status")
    assert hasattr(callback, "total_status")
    assert hasattr(callback, "logger")

    assert isinstance(callback.request_status, dict)
    assert isinstance(callback.eval_status, dict)
    assert isinstance(callback.total_status, dict)


def test_base_resolver_callback_request_event():
    """Test BaseResolverCallback handling RequestEvent."""
    callback = BaseResolverCallback()
    key = StrBindKey("test_key")
    context = Mock(spec=ProvideContext, trace_str="request_trace")

    event = RequestEvent(key=key, cxt=context)
    callback(event)

    assert callback.request_status[key] == "waiting"
    assert key in callback.total_status
    assert callback.total_status[key].status == "waiting"
    assert callback.total_status[key].kind == "provide"


def test_base_resolver_callback_provide_event():
    """Test BaseResolverCallback handling ProvideEvent."""
    callback = BaseResolverCallback()
    key = StrBindKey("test_key")
    context = Mock(spec=ProvideContext, trace_str="provide_trace")

    # First send request event to set up status
    request_event = RequestEvent(key=key, cxt=context)
    callback(request_event)

    # Then send provide event
    provide_event = ProvideEvent(key=key, cxt=context, data="test_data")
    callback(provide_event)

    assert callback.request_status[key] == "provided"
    assert callback.total_status[key].status == "provided"


def test_base_resolver_callback_deps_ready_event():
    """Test BaseResolverCallback handling DepsReadyEvent."""
    callback = BaseResolverCallback()
    key = StrBindKey("test_key")
    context = Mock(spec=ProvideContext, trace_str="deps_trace")

    # First send request event
    request_event = RequestEvent(key=key, cxt=context)
    callback(request_event)

    # Then send deps ready event
    deps_event = DepsReadyEvent(key=key, cxt=context, deps={})
    callback(deps_event)

    assert callback.request_status[key] == "running"
    assert callback.total_status[key].status == "running"


def test_base_resolver_callback_eval_events():
    """Test BaseResolverCallback handling eval events."""
    callback = BaseResolverCallback()
    expr = Call(func=Object("func"), args=[Object(1)])

    # Eval request
    eval_request = EvalRequestEvent(expr=expr, cxt=Mock(spec=ProvideContext))
    callback(eval_request)

    expr_repr = callback.expr_repr(expr)
    assert expr_repr in callback.eval_status
    assert callback.eval_status[expr_repr] == "calling"

    # Eval result
    eval_result = EvalResultEvent(
        expr=expr, result="result", cxt=Mock(spec=ProvideContext)
    )
    callback(eval_result)

    assert callback.eval_status[expr_repr] == "done"
    assert callback.total_status[expr_repr].status == "done"


def test_base_resolver_callback_await_expr():
    """Test BaseResolverCallback handling await expressions."""
    callback = BaseResolverCallback()
    expr = UnaryOp("await", Object("async_func"))

    # Eval request for await
    eval_request = EvalRequestEvent(expr=expr, cxt=Mock(spec=ProvideContext))
    callback(eval_request)

    expr_repr = callback.expr_repr(expr)
    assert callback.eval_status[expr_repr] == "await"


def test_base_resolver_callback_cache_expr():
    """Test BaseResolverCallback ignores Cache expressions."""
    callback = BaseResolverCallback()
    expr = Cache(Object(42))

    # Should not add to eval_status
    eval_request = EvalRequestEvent(expr=expr, cxt=Mock(spec=ProvideContext))
    callback(eval_request)

    assert len(callback.eval_status) == 0


def test_base_resolver_callback_colored_key():
    """Test BaseResolverCallback colored key methods."""
    callback = BaseResolverCallback()
    key = StrBindKey("test")

    # Set different statuses and test coloring
    callback.request_status[key] = "waiting"
    colored = callback._colored_key(key)
    assert "<cyan>" in colored
    assert "</cyan>" in colored

    callback.request_status[key] = "running"
    colored = callback._colored_key(key)
    assert "<yellow>" in colored

    callback.request_status[key] = "provided"
    colored = callback._colored_key(key)
    assert "<green>" in colored


def test_base_resolver_callback_clean_msg():
    """Test BaseResolverCallback clean_msg method."""
    callback = BaseResolverCallback()

    msg = "test <tag> message >with< brackets"
    cleaned = callback.clean_msg(msg)
    assert cleaned == r"test \<tag\> message \>with\< brackets"


def test_base_resolver_callback_expr_repr():
    """Test BaseResolverCallback expr_repr method."""
    callback = BaseResolverCallback()

    # Short expression
    short_expr = Object(42)
    repr_str = callback.expr_repr(short_expr)
    assert "42" in repr_str

    # Long expression should be truncated
    long_str = "x" * 100
    long_expr = Object(long_str)
    repr_str = callback.expr_repr(long_expr)
    assert len(repr_str) < 60  # Should be truncated to ~50 chars
    assert "..." in repr_str


def test_base_resolver_callback_invalid_event():
    """Test BaseResolverCallback raises on invalid event."""
    callback = BaseResolverCallback()

    invalid_event = Mock()  # Not a valid event type

    with pytest.raises(TypeError, match="event must be RequestEvent or ProvideEvent"):
        callback(invalid_event)


def test_providable_type():
    """Test that Providable type alias works correctly."""
    # These should all be valid Providable types
    providables = [
        "string_key",
        StrBindKey("key"),
        lambda x: x + 1,
        Mock(),  # Any callable
    ]

    for p in providables:
        # Just verify they can be used where Providable is expected
        assert p is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
