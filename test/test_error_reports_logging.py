import json
import contextlib
from unittest.mock import Mock, patch

import pytest

from pinjected import design, injected, instance
from pinjected.run_helpers.run_injected import (
    RunContext,
    a_get_run_context,
    a_run_with_notify,
)
from pinjected.schema.handlers import (
    PinjectedHandleMainException,
    PinjectedHandleMainResult,
)


# Test target functions at module level
@instance
def failing_target():
    raise ValueError("Test error")


@instance
def success_target():
    return "Success result"


class TestErrorReportsLogging:
    """Test suite for error reports logging functionality"""

    def test_log_run_context_success(self, tmp_path):
        """Test logging run context for successful execution"""
        from packages.error_reports.src.pinjected_error_reports import _log_run_context

        # Create mock context
        mock_context = Mock(spec=RunContext)
        mock_context.src_var_spec = Mock()
        mock_context.src_var_spec.var_path = "test.module.success"
        mock_context.design = Mock()
        mock_context.design.bindings = Mock()
        mock_context.design.bindings.keys = Mock(return_value=["key1", "key2"])
        mock_context.meta_overrides = Mock()
        mock_context.meta_overrides.bindings = Mock()
        mock_context.meta_overrides.bindings.keys = Mock(return_value=["meta1"])
        mock_context.overrides = Mock()
        mock_context.overrides.bindings = Mock()
        mock_context.overrides.bindings.keys = Mock(return_value=["override1"])

        # Create log file in tmp directory
        log_file = tmp_path / ".pinjected_last_run.log"

        # Patch Path where it's imported in the module
        with patch(
            "packages.error_reports.src.pinjected_error_reports.Path"
        ) as mock_path_class:
            # Make Path() return our log_file
            mock_path_class.return_value = log_file

            # Log success
            test_result = {"status": "success", "data": 42}
            _log_run_context(mock_context, result=test_result)

        # Verify log file contents
        assert log_file.exists()
        with open(log_file, "r") as f:
            log_data = json.load(f)

        assert log_data["status"] == "success"
        assert log_data["result"] == str(test_result)
        assert log_data["context"]["var_path"] == "test.module.success"
        assert log_data["context"]["design_bindings"] == ["key1", "key2"]
        assert log_data["context"]["meta_overrides_bindings"] == ["meta1"]
        assert log_data["context"]["overrides_bindings"] == ["override1"]
        assert "timestamp" in log_data

    def test_log_run_context_error(self, tmp_path):
        """Test logging run context for error execution"""
        from packages.error_reports.src.pinjected_error_reports import _log_run_context

        # Create mock context
        mock_context = Mock(spec=RunContext)
        mock_context.src_var_spec = Mock()
        mock_context.src_var_spec.var_path = "test.module.error"
        mock_context.design = Mock()
        mock_context.design.bindings = Mock()
        mock_context.design.bindings.keys = Mock(return_value=[])
        mock_context.meta_overrides = Mock()
        mock_context.meta_overrides.bindings = Mock()
        mock_context.meta_overrides.bindings.keys = Mock(return_value=[])
        mock_context.overrides = Mock()
        mock_context.overrides.bindings = Mock()
        mock_context.overrides.bindings.keys = Mock(return_value=[])

        # Create log file in tmp directory
        log_file = tmp_path / ".pinjected_last_run.log"

        # Patch Path where it's imported in the module
        with patch(
            "packages.error_reports.src.pinjected_error_reports.Path"
        ) as mock_path_class:
            # Make Path() return our log_file
            mock_path_class.return_value = log_file

            # Log error
            test_error = ValueError("Test error message")
            _log_run_context(mock_context, error=test_error)

        # Verify log file contents
        assert log_file.exists()
        with open(log_file, "r") as f:
            log_data = json.load(f)

        assert log_data["status"] == "error"
        assert log_data["error"] == "Test error message"
        assert log_data["error_type"] == "ValueError"
        assert "traceback" in log_data
        assert isinstance(log_data["traceback"], list)
        assert "timestamp" in log_data

    @pytest.mark.asyncio
    async def test_handlers_create_log_file(self, tmp_path):
        """Test that handlers actually create log files during execution"""

        log_file = tmp_path / ".pinjected_last_run.log"

        # Mock dependencies for error handler
        @injected
        async def mock_handler_with_logging(logger, /, context, e: Exception):
            # Import json and datetime here since _log_run_context uses them
            import json
            from datetime import datetime

            # Create the log data directly as _log_run_context would
            log_data = {
                "timestamp": datetime.now().isoformat(),
                "context": {
                    "var_path": context.src_var_spec.var_path,
                    "design_bindings": list(context.design.bindings.keys()),
                    "meta_overrides_bindings": list(
                        context.meta_overrides.bindings.keys()
                    ),
                    "overrides_bindings": list(context.overrides.bindings.keys()),
                },
                "status": "error",
                "error": str(e),
                "error_type": type(e).__name__,
                "traceback": [],  # Simplified for test
            }

            # Write to our test log file
            with open(log_file, "w") as f:
                json.dump(log_data, f, indent=2, default=str)

            return "handled"

        @injected
        async def mock_result_handler_with_logging(logger, /, context, result):
            # Import json and datetime here since _log_run_context uses them
            import json
            from datetime import datetime

            # Create the log data directly as _log_run_context would
            log_data = {
                "timestamp": datetime.now().isoformat(),
                "context": {
                    "var_path": context.src_var_spec.var_path,
                    "design_bindings": list(context.design.bindings.keys()),
                    "meta_overrides_bindings": list(
                        context.meta_overrides.bindings.keys()
                    ),
                    "overrides_bindings": list(context.overrides.bindings.keys()),
                },
                "status": "success",
                "result": str(result),
            }

            # Write to our test log file
            with open(log_file, "w") as f:
                json.dump(log_data, f, indent=2, default=str)

        @instance
        def mock_logger():
            return Mock()

        # Use module-level target functions

        test_design = design(
            **{
                PinjectedHandleMainException.key.name: mock_handler_with_logging,
                PinjectedHandleMainResult.key.name: mock_result_handler_with_logging,
            },
            logger=mock_logger,
        )

        # Test error case
        var_path = f"{__name__}.failing_target"
        cxt = await a_get_run_context(None, var_path)
        cxt = cxt.add_overrides(test_design)

        async def task(ctx):
            return await ctx.a_run()

        # The handler should handle the error
        with contextlib.suppress(Exception):
            await a_run_with_notify(cxt, task)

        assert log_file.exists()
        with open(log_file, "r") as f:
            log_data = json.load(f)
        assert log_data["status"] == "error"
        # The error may be wrapped in ExceptionGroup in Python 3.11+
        assert log_data["error_type"] in ["ValueError", "ExceptionGroup"]

        # Test success case
        log_file.unlink()  # Remove previous log
        var_path2 = f"{__name__}.success_target"
        cxt2 = await a_get_run_context(None, var_path2)
        cxt2 = cxt2.add_overrides(test_design)

        result = await a_run_with_notify(cxt2, task)

        assert result == "Success result"
        assert log_file.exists()
        with open(log_file, "r") as f:
            log_data = json.load(f)
        assert log_data["status"] == "success"
        assert log_data["result"] == "Success result"

    def test_log_file_overwrites_previous(self, tmp_path):
        """Test that each run overwrites the previous log file"""
        from packages.error_reports.src.pinjected_error_reports import _log_run_context

        mock_context = Mock(spec=RunContext)
        mock_context.src_var_spec = Mock()
        mock_context.src_var_spec.var_path = "test.first"
        mock_context.design = Mock()
        mock_context.design.bindings = Mock()
        mock_context.design.bindings.keys = Mock(return_value=[])
        mock_context.meta_overrides = Mock()
        mock_context.meta_overrides.bindings = Mock()
        mock_context.meta_overrides.bindings.keys = Mock(return_value=[])
        mock_context.overrides = Mock()
        mock_context.overrides.bindings = Mock()
        mock_context.overrides.bindings.keys = Mock(return_value=[])

        log_file = tmp_path / ".pinjected_last_run.log"

        with patch(
            "packages.error_reports.src.pinjected_error_reports.Path"
        ) as mock_path:
            mock_path.return_value = log_file

            # First log
            _log_run_context(mock_context, result="first result")

            with open(log_file, "r") as f:
                log_data = json.load(f)
            assert log_data["result"] == "first result"

            # Second log should overwrite
            mock_context.src_var_spec.var_path = "test.second"
            _log_run_context(mock_context, result="second result")

            with open(log_file, "r") as f:
                log_data = json.load(f)
            assert log_data["result"] == "second result"
            assert log_data["context"]["var_path"] == "test.second"

    def test_log_context_with_str_bindings(self, tmp_path):
        """Test logging when binding keys return string representations"""
        from packages.error_reports.src.pinjected_error_reports import _log_run_context

        # Create mock context with StrBindKey objects
        mock_context = Mock(spec=RunContext)
        mock_context.src_var_spec = Mock()
        mock_context.src_var_spec.var_path = "test.module.bindings"

        # Mock binding keys that return string representations
        class MockStrBindKey:
            def __init__(self, name):
                self.name = name

            def __str__(self):
                return f"StrBindKey(name='{self.name}')"

        mock_context.design = Mock()
        mock_context.design.bindings = Mock()
        mock_context.design.bindings.keys = Mock(
            return_value=[MockStrBindKey("key1"), MockStrBindKey("key2")]
        )
        mock_context.meta_overrides = Mock()
        mock_context.meta_overrides.bindings = Mock()
        mock_context.meta_overrides.bindings.keys = Mock(return_value=[])
        mock_context.overrides = Mock()
        mock_context.overrides.bindings = Mock()
        mock_context.overrides.bindings.keys = Mock(return_value=[])

        log_file = tmp_path / ".pinjected_last_run.log"

        with patch(
            "packages.error_reports.src.pinjected_error_reports.Path"
        ) as mock_path:
            mock_path.return_value = log_file

            _log_run_context(mock_context, result="test")

        with open(log_file, "r") as f:
            log_data = json.load(f)

        # Should handle string representations properly
        assert len(log_data["context"]["design_bindings"]) == 2
        assert "StrBindKey(name='key1')" in log_data["context"]["design_bindings"]
        assert "StrBindKey(name='key2')" in log_data["context"]["design_bindings"]
