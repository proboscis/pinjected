import contextlib
import sys
from unittest.mock import Mock

import pytest

# Use the appropriate ExceptionGroup based on Python version
if sys.version_info >= (3, 11):
    # Python 3.11+ has native ExceptionGroup
    ExceptionGroup = BaseExceptionGroup  # noqa: F821
else:
    # Python < 3.11 uses our compatibility ExceptionGroup
    from pinjected.compatibility.task_group import ExceptionGroup

from pinjected import design, injected, instance
from pinjected.run_helpers.run_injected import (
    RunContext,
    a_run_with_notify,
    a_get_run_context,
)
from pinjected.schema.handlers import (
    PinjectedHandleMainException,
    PinjectedHandleMainResult,
)


# Test target functions need to be at module level for import
@instance
def failing_target():
    raise ValueError("Test error")


@instance
def successful_target():
    return {"status": "success", "data": 42}


@instance
def target_with_data():
    return "test_result"


@instance
def failing_func():
    raise RuntimeError("Test error")


@instance
def target_func():
    return "test_value"


@instance
def success_func():
    return "success"


@instance
def fail_func():
    raise ValueError("fail")


class TestHandlersWithContext:
    """Test suite for handlers with RunContext parameter"""

    @pytest.fixture
    def mock_context(self):
        """Create a mock RunContext for testing"""
        context = Mock(spec=RunContext)
        context.src_var_spec = Mock()
        context.src_var_spec.var_path = "test.module.var"
        context.design = Mock()
        context.design.bindings = Mock()
        context.design.bindings.keys = Mock(return_value=["key1", "key2"])
        context.meta_overrides = Mock()
        context.meta_overrides.bindings = Mock()
        context.meta_overrides.bindings.keys = Mock(return_value=["meta1", "meta2"])
        context.overrides = Mock()
        context.overrides.bindings = Mock()
        context.overrides.bindings.keys = Mock(return_value=["override1", "override2"])
        context.get_final_design = Mock()
        context.a_provide = Mock()
        return context

    @pytest.mark.asyncio
    async def test_exception_handler_receives_context(self):
        """Test that exception handler receives context as first parameter"""
        handler_called = False
        received_context = None
        received_exception = None

        @injected
        async def test_exception_handler(context, e: Exception):
            nonlocal handler_called, received_context, received_exception
            handler_called = True
            received_context = context
            received_exception = e
            return "handled"

        test_design = design(
            **{
                PinjectedHandleMainException.key.name: test_exception_handler,
            }
        )

        # Get run context and execute with handler
        var_path = f"{__name__}.failing_target"
        cxt = await a_get_run_context(None, var_path)
        cxt = cxt.add_overrides(test_design)

        async def task(ctx):
            return await ctx.a_run()

        with contextlib.suppress(ExceptionGroup):
            await a_run_with_notify(
                cxt, task
            )  # Expected - handler should still be called

        assert handler_called, "Exception handler should have been called"
        assert received_context is not None, "Handler should have received context"
        assert hasattr(received_context, "src_var_spec"), (
            "Context should have src_var_spec"
        )
        # In Python 3.11+, TaskGroup wraps exceptions in ExceptionGroup
        if (
            hasattr(received_exception, "__class__")
            and "ExceptionGroup" in received_exception.__class__.__name__
        ):
            # Extract the actual exception from ExceptionGroup
            assert len(received_exception.exceptions) == 1
            actual_exception = received_exception.exceptions[0]
            assert isinstance(actual_exception, ValueError), (
                "Handler should have received the ValueError"
            )
            assert str(actual_exception) == "Test error"
        else:
            # Direct exception for older Python versions
            assert isinstance(received_exception, ValueError), (
                "Handler should have received the exception"
            )
            assert str(received_exception) == "Test error"

    @pytest.mark.asyncio
    async def test_result_handler_receives_context(self):
        """Test that result handler receives context as first parameter"""
        handler_called = False
        received_context = None
        received_result = None

        @injected
        async def test_result_handler(context, result):
            nonlocal handler_called, received_context, received_result
            handler_called = True
            received_context = context
            received_result = result

        test_design = design(
            **{
                PinjectedHandleMainResult.key.name: test_result_handler,
            }
        )

        # Get run context and execute with handler
        var_path = f"{__name__}.successful_target"
        cxt = await a_get_run_context(None, var_path)
        cxt = cxt.add_overrides(test_design)

        async def task(ctx):
            return await ctx.a_run()

        await a_run_with_notify(cxt, task)

        assert handler_called, "Result handler should have been called"
        assert received_context is not None, "Handler should have received context"
        assert hasattr(received_context, "src_var_spec"), (
            "Context should have src_var_spec"
        )
        assert received_result == {"status": "success", "data": 42}

    @pytest.mark.asyncio
    async def test_handler_can_access_context_attributes(self):
        """Test that handlers can access context attributes like design bindings"""
        context_data = {}

        @injected
        async def capturing_handler(context, result):
            context_data["var_path"] = context.src_var_spec.var_path
            context_data["design_keys"] = list(context.design.bindings.keys())
            context_data["has_meta_overrides"] = hasattr(context, "meta_overrides")
            context_data["has_overrides"] = hasattr(context, "overrides")

        test_design = design(
            **{
                PinjectedHandleMainResult.key.name: capturing_handler,
            },
            test_key="test_value",
        )

        # Get run context and execute with handler
        var_path = f"{__name__}.target_with_data"
        cxt = await a_get_run_context(None, var_path)
        cxt = cxt.add_overrides(test_design)

        async def task(ctx):
            return await ctx.a_run()

        await a_run_with_notify(cxt, task)

        assert "var_path" in context_data
        assert __name__ in context_data["var_path"]
        assert "target_with_data" in context_data["var_path"]
        assert context_data["has_meta_overrides"]
        assert context_data["has_overrides"]

    @pytest.mark.asyncio
    async def test_exception_handler_return_value(self):
        """Test that exception handler return value affects exception propagation"""

        @injected
        async def handler_returns_handled(context, e: Exception):
            return "handled"

        @injected
        async def handler_returns_none(context, e: Exception):
            return None

        # Test handler that returns "handled" - exception should still be raised
        design_handled = design(
            **{
                PinjectedHandleMainException.key.name: handler_returns_handled,
            }
        )

        var_path = f"{__name__}.failing_func"
        cxt = await a_get_run_context(None, var_path)
        cxt = cxt.add_overrides(design_handled)

        async def task(ctx):
            return await ctx.a_run()

        with pytest.raises((RuntimeError, ExceptionGroup)) as exc_info:
            await a_run_with_notify(cxt, task)
        # Handle both direct RuntimeError and ExceptionGroup
        if (
            hasattr(exc_info.value, "__class__")
            and "ExceptionGroup" in exc_info.value.__class__.__name__
        ):
            assert len(exc_info.value.exceptions) == 1
            actual_exception = exc_info.value.exceptions[0]
            assert isinstance(actual_exception, RuntimeError)
            assert str(actual_exception) == "Test error"
        else:
            assert str(exc_info.value) == "Test error"

        # Test handler that returns None - exception should still be raised
        design_none = design(
            **{
                PinjectedHandleMainException.key.name: handler_returns_none,
            }
        )

        cxt2 = await a_get_run_context(None, var_path)
        cxt2 = cxt2.add_overrides(design_none)

        with pytest.raises((RuntimeError, ExceptionGroup)) as exc_info:
            await a_run_with_notify(cxt2, task)
        # Handle both direct RuntimeError and ExceptionGroup
        if (
            hasattr(exc_info.value, "__class__")
            and "ExceptionGroup" in exc_info.value.__class__.__name__
        ):
            assert len(exc_info.value.exceptions) == 1
            actual_exception = exc_info.value.exceptions[0]
            assert isinstance(actual_exception, RuntimeError)
            assert str(actual_exception) == "Test error"
        else:
            assert str(exc_info.value) == "Test error"

    @pytest.mark.asyncio
    async def test_handler_with_dependency_injection(self):
        """Test that handlers can use dependency injection"""

        @injected
        async def handler_with_deps(logger, custom_service, /, context, result):
            logger_msg = f"Logged: {result}"
            service_msg = custom_service(result)
            return f"{logger_msg} | {service_msg}"

        @instance
        def mock_logger():
            return Mock()

        @instance
        def custom_service():
            return lambda x: f"Processed: {x}"

        test_design = design(
            **{
                PinjectedHandleMainResult.key.name: handler_with_deps,
            },
            logger=mock_logger,
            custom_service=custom_service,
        )

        var_path = f"{__name__}.target_func"
        cxt = await a_get_run_context(None, var_path)
        cxt = cxt.add_overrides(test_design)

        async def task(ctx):
            return await ctx.a_run()

        result = await a_run_with_notify(cxt, task)

        assert result == "test_value"

    @pytest.mark.asyncio
    async def test_a_run_with_notify_direct(self):
        """Test a_run_with_notify function directly with mock context"""
        mock_context = Mock(spec=RunContext)
        mock_context.get_final_design = Mock(return_value=design())

        result_from_task = "test_result"

        async def mock_task(ctx):
            assert ctx is mock_context
            return result_from_task

        # Test without handlers
        result = await a_run_with_notify(mock_context, mock_task)
        assert result == result_from_task

        # Test with exception
        async def failing_task(ctx):
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            await a_run_with_notify(mock_context, failing_task)

    @pytest.mark.asyncio
    async def test_both_handlers_in_same_run(self):
        """Test that both exception and result handlers can be used together"""
        exception_handler_called = False
        result_handler_called = False

        @injected
        async def exc_handler(context, e: Exception):
            nonlocal exception_handler_called
            exception_handler_called = True

        @injected
        async def res_handler(context, result):
            nonlocal result_handler_called
            result_handler_called = True

        test_design = design(
            **{
                PinjectedHandleMainException.key.name: exc_handler,
                PinjectedHandleMainResult.key.name: res_handler,
            }
        )

        # Test success case - only result handler should be called
        var_path = f"{__name__}.success_func"
        cxt = await a_get_run_context(None, var_path)
        cxt = cxt.add_overrides(test_design)

        async def task(ctx):
            return await ctx.a_run()

        result = await a_run_with_notify(cxt, task)
        assert result == "success"
        assert not exception_handler_called
        assert result_handler_called

        # Reset flags
        exception_handler_called = False
        result_handler_called = False

        # Test failure case - only exception handler should be called
        var_path2 = f"{__name__}.fail_func"
        cxt2 = await a_get_run_context(None, var_path2)
        cxt2 = cxt2.add_overrides(test_design)

        with pytest.raises((ValueError, ExceptionGroup)):
            await a_run_with_notify(cxt2, task)
        assert exception_handler_called
        assert not result_handler_called
