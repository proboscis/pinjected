"""Simple tests for v2/resolver.py module."""

import pytest
from unittest.mock import Mock, patch
from dataclasses import is_dataclass

from pinjected.v2.resolver import EvaluationError, ResolveStatus, BaseResolverCallback
from pinjected.v2.async_resolver import AsyncResolver
from pinjected.v2.keys import StrBindKey


class TestEvaluationError:
    """Test the EvaluationError class."""

    def test_evaluation_error_creation(self):
        """Test EvaluationError creation."""
        from pinjected.v2.provide_context import ProvideContext
        from pinjected.di.expr_util import Object

        ctx = Mock(spec=ProvideContext)
        ctx.trace_str = "A -> B"
        ctx_expr = Object("context")
        cause_expr = Object("cause")
        src = ValueError("Test error")

        error = EvaluationError(ctx, ctx_expr, cause_expr, src)

        assert error.cxt == ctx
        assert error.cxt_expr == ctx_expr
        assert error.cause_expr == cause_expr
        assert error.src == src
        assert isinstance(error, Exception)

    def test_evaluation_error_string_representation(self):
        """Test EvaluationError string representation."""
        from pinjected.v2.provide_context import ProvideContext
        from pinjected.di.expr_util import Object

        ctx = Mock(spec=ProvideContext)
        ctx.trace_str = "test_trace"
        error = EvaluationError(ctx, Object("ctx"), Object("cause"), ValueError())

        error_str = str(error)
        assert "EvaluationError" in error_str
        assert "Context:" in error_str


class TestResolveStatus:
    """Test the ResolveStatus dataclass."""

    def test_resolve_status_is_dataclass(self):
        """Test that ResolveStatus is a dataclass."""
        assert is_dataclass(ResolveStatus)

    def test_resolve_status_creation(self):
        """Test creating ResolveStatus instance."""
        import datetime

        key = StrBindKey("test")
        status = ResolveStatus(
            key=key,
            kind="provide",
            status="waiting",
            start=datetime.datetime.now(),
            end=None,
        )

        assert status.key == key
        assert status.kind == "provide"
        assert status.status == "waiting"
        assert status.start is not None
        assert status.end is None


class TestBaseResolverCallback:
    """Test the BlockingResolver class."""

    def test_base_resolver_callback_is_dataclass(self):
        """Test that BaseResolverCallback is a dataclass."""
        assert is_dataclass(BaseResolverCallback)

    def test_base_resolver_callback_creation(self):
        """Test creating BaseResolverCallback instance."""
        callback = BaseResolverCallback()

        assert hasattr(callback, "request_status")
        assert hasattr(callback, "eval_status")
        assert hasattr(callback, "total_status")
        assert hasattr(callback, "logger")

    def test_base_resolver_callback_call_method(self):
        """Test BaseResolverCallback __call__ method."""
        from pinjected.v2.events import RequestEvent

        callback = BaseResolverCallback()

        # Create a mock event
        event = Mock(spec=RequestEvent)
        event.key = StrBindKey("test")
        event.cxt = Mock()
        event.cxt.trace_str = "test_trace"

        # Should be callable
        assert callable(callback)

        # Call with event - should handle it
        with patch.object(callback, "on_request") as mock_on_request:
            callback(event)
            mock_on_request.assert_called_once_with(event)

    def test_base_resolver_callback_status_methods(self):
        """Test status string methods."""
        callback = BaseResolverCallback()

        # Add some status
        callback.request_status[StrBindKey("test")] = "waiting"

        # Should have status string methods
        assert hasattr(callback, "provider_status_string")
        assert hasattr(callback, "eval_status_string")
        assert hasattr(callback, "total_status_string")

        # Should be able to call them
        provider_str = callback.provider_status_string()
        assert isinstance(provider_str, str)

    def test_base_resolver_callback_event_handlers(self):
        """Test event handler methods exist."""
        callback = BaseResolverCallback()

        # Check all event handlers exist
        assert hasattr(callback, "on_request")
        assert hasattr(callback, "on_provide")
        assert hasattr(callback, "on_deps_ready")
        assert hasattr(callback, "on_eval_request")
        assert hasattr(callback, "on_eval_result")
        assert hasattr(callback, "on_call_in_eval_start")
        assert hasattr(callback, "on_call_in_eval_end")


class TestBlockingResolver:
    """Test the blocking resolver from blocking_resolver.py."""

    def test_blocking_resolver_import(self):
        """Test that we can import Resolver from blocking_resolver."""
        from pinjected.v2.blocking_resolver import Resolver

        assert Resolver is not None
        assert is_dataclass(Resolver)

    def test_blocking_resolver_structure(self):
        """Test Resolver has expected methods."""
        from pinjected.v2.blocking_resolver import Resolver

        async_resolver = Mock(spec=AsyncResolver)
        resolver = Resolver(resolver=async_resolver)

        assert hasattr(resolver, "provide")
        assert hasattr(resolver, "child_session")
        assert hasattr(resolver, "to_async")
        assert hasattr(resolver, "__getitem__")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
