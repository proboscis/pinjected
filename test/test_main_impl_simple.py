"""Simple tests to improve coverage for pinjected/main_impl.py."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import asyncio
import json
import base64

from pinjected.main_impl import (
    run,
    check_config,
    parse_kwargs_as_design,
    parse_overrides,
    decode_b64json,
    call,
    json_graph,
    describe,
    describe_json,
    list,
    trace_key,
    PinjectedCLI,
    main,
    _print_trace_key_error,
    _handle_trace_results,
    PinjectedRunDependencyResolutionFailure,
)
from pinjected import design, Design, Injected
from pinjected.di.proxiable import DelegatedVar


class TestParseKwargsAsDesign:
    """Test parse_kwargs_as_design function."""

    def test_simple_kwargs(self):
        """Test parsing simple kwargs."""
        result = parse_kwargs_as_design(a="value1", b=123)
        assert isinstance(result, Design)

    def test_module_path_format(self):
        """Test parsing {module.path} format."""
        with patch("pinjected.main_impl.load_variable_by_module_path") as mock_load:
            mock_load.return_value = "loaded_value"
            result = parse_kwargs_as_design(key="{my.module.var}")
            mock_load.assert_called_once_with("my.module.var")
            assert isinstance(result, Design)

    def test_mixed_kwargs(self):
        """Test parsing mixed kwargs."""
        with patch("pinjected.main_impl.load_variable_by_module_path") as mock_load:
            mock_load.return_value = "loaded"
            result = parse_kwargs_as_design(a="simple", b="{module.var}", c=42)
            assert isinstance(result, Design)
            mock_load.assert_called_once_with("module.var")

    def test_empty_kwargs(self):
        """Test parsing empty kwargs."""
        result = parse_kwargs_as_design()
        assert isinstance(result, Design)


class TestParseOverrides:
    """Test parse_overrides function."""

    def test_none_overrides(self):
        """Test None overrides."""
        result = parse_overrides(None)
        assert isinstance(result, Design)

    def test_design_path_with_colon(self):
        """Test design_path:var format."""
        with patch("pinjected.main_impl.run_injected") as mock_run:
            mock_design = design(test="value")
            mock_run.return_value = mock_design

            result = parse_overrides("my.design:my_var")

            mock_run.assert_called_once_with(
                "get", "my_var", "my.design", return_result=True
            )
            assert result == mock_design

    def test_module_path_design(self):
        """Test loading Design from module path."""
        with patch("pinjected.main_impl.ModuleVarPath") as mock_mvp:
            mock_design = design(test="value")
            mock_mvp.return_value.load.return_value = mock_design

            result = parse_overrides("my.module.design")

            assert result == mock_design

    def test_module_path_injected(self):
        """Test loading Injected from module path."""
        with (
            patch("pinjected.main_impl.ModuleVarPath") as mock_mvp,
            patch("pinjected.main_impl.run_injected") as mock_run,
        ):
            mock_injected = Mock(spec=Injected)
            mock_mvp.return_value.load.return_value = mock_injected
            mock_design = design(test="value")
            mock_run.return_value = mock_design

            result = parse_overrides("my.module.injected")

            mock_run.assert_called_once_with(
                "get", "my.module.injected", return_result=True
            )
            assert result == mock_design

    def test_module_path_delegated_var(self):
        """Test loading DelegatedVar from module path."""
        with (
            patch("pinjected.main_impl.ModuleVarPath") as mock_mvp,
            patch("pinjected.main_impl.run_injected") as mock_run,
        ):
            mock_var = Mock(spec=DelegatedVar)
            mock_mvp.return_value.load.return_value = mock_var
            mock_design = design(test="value")
            mock_run.return_value = mock_design

            result = parse_overrides("my.module.var")

            assert result == mock_design


class TestDecodeB64Json:
    """Test decode_b64json function."""

    def test_decode_valid(self):
        """Test decoding valid base64 JSON."""
        data = {"key": "value", "num": 42}
        encoded = base64.b64encode(json.dumps(data).encode()).decode()

        result = decode_b64json(encoded)
        assert result == data

    def test_decode_empty_dict(self):
        """Test decoding empty dict."""
        data = {}
        encoded = base64.b64encode(json.dumps(data).encode()).decode()

        result = decode_b64json(encoded)
        assert result == data


class TestCheckConfig:
    """Test check_config function."""

    def test_check_config(self):
        """Test check_config displays designs."""
        with (
            patch("pinjected.main_impl.load_user_default_design") as mock_default,
            patch("pinjected.main_impl.load_user_overrides_design") as mock_overrides,
            patch("pinjected.pinjected_logging.logger") as mock_logger,
        ):
            mock_design1 = Mock()
            mock_design1.table_str.return_value = "default table"
            mock_design2 = Mock()
            mock_design2.table_str.return_value = "overrides table"

            mock_default.return_value = mock_design1
            mock_overrides.return_value = mock_design2

            check_config()

            assert mock_logger.info.call_count == 4
            mock_logger.info.assert_any_call("displaying default design bindings:")
            mock_logger.info.assert_any_call("default table")
            mock_logger.info.assert_any_call("displaying overrides design bindings:")
            mock_logger.info.assert_any_call("overrides table")


class TestJsonGraph:
    """Test json_graph function."""

    def test_json_graph(self):
        """Test json_graph delegates to run_injected."""
        with patch("pinjected.main_impl.run_injected") as mock_run:
            mock_run.return_value = {"graph": "data"}

            result = json_graph("my.var", "my.design", extra="param")

            mock_run.assert_called_once_with(
                "json-graph", "my.var", "my.design", extra="param"
            )
            assert result == {"graph": "data"}


class TestDescribe:
    """Test describe function."""

    def test_describe_no_var_path(self):
        """Test describe with no var_path."""
        with patch("builtins.print") as mock_print:
            result = describe()

            assert result is None
            assert mock_print.call_count >= 1
            mock_print.assert_any_call(
                "Error: You must provide a variable path in the format 'full.module.path.var.name'"
            )

    def test_describe_with_var_path(self):
        """Test describe with var_path."""
        with patch("pinjected.main_impl.run_injected") as mock_run:
            mock_run.return_value = "description"

            result = describe("my.var", "my.design")

            mock_run.assert_called_once_with("describe", "my.var", "my.design")
            assert result == "description"


class TestDescribeJson:
    """Test describe_json function."""

    def test_describe_json_no_var_path(self):
        """Test describe_json with no var_path."""
        with patch("builtins.print") as mock_print:
            result = describe_json()

            assert result is None
            assert mock_print.call_count >= 1

    def test_describe_json_with_var_path(self):
        """Test describe_json with var_path."""
        with patch("pinjected.main_impl.run_injected") as mock_run:
            mock_run.return_value = {"json": "data"}

            describe_json("my.var", "my.design")

            mock_run.assert_called_once_with("describe_json", "my.var", "my.design")


class TestList:
    """Test list function."""

    def test_list_no_var_path(self):
        """Test list with no var_path."""
        with patch("builtins.print") as mock_print:
            result = list()

            assert result is None
            assert mock_print.call_count >= 1

    def test_list_success(self):
        """Test list function succeeds with mocked dependencies."""
        # Simple test just checking success case
        # Create test module
        test_module = type("module", (), {"__file__": __file__})()

        # The actual print goes to stdout, so we'll just ensure the function runs
        with patch("importlib.import_module", return_value=test_module):
            from pinjected import runnables

            with patch.object(runnables, "get_runnables", return_value=[]):
                result = list("test.module")
                # Should return 0 on success
                assert result == 0

    def test_list_import_error(self):
        """Test list with import error."""
        with patch("importlib.import_module") as mock_import, patch("builtins.print"):
            mock_import.side_effect = ImportError("Module not found")

            result = list("bad.module")

            # The print function is not mocked properly because it prints to stdout directly
            # Just check the result code
            assert result == 1

    def test_list_general_error(self):
        """Test list with general error."""
        with patch("importlib.import_module") as mock_import, patch("builtins.print"):
            mock_import.side_effect = RuntimeError("Unexpected error")

            result = list("my.module")

            # The print function is not mocked properly because it prints to stdout directly
            # Just check the result code
            assert result == 1


class TestTraceKey:
    """Test trace_key functions."""

    def test_print_trace_key_error(self):
        """Test _print_trace_key_error."""
        with patch("builtins.print") as mock_print:
            _print_trace_key_error()

            assert mock_print.call_count >= 1
            mock_print.assert_any_call("Error: You must provide a key name to trace")

    def test_handle_trace_results_not_found(self):
        """Test _handle_trace_results when key not found."""
        with patch("builtins.print") as mock_print:
            result = _handle_trace_results("mykey", [], False)

            assert result == 0
            mock_print.assert_called_once_with(
                "Key 'mykey' not found in the design hierarchy"
            )

    def test_handle_trace_results_no_traces(self):
        """Test _handle_trace_results with no traces."""
        with patch("builtins.print") as mock_print:
            result = _handle_trace_results("mykey", [], True)

            assert result == 0
            mock_print.assert_called_once_with(
                "Key 'mykey' exists but no trace information available"
            )

    def test_handle_trace_results_with_traces(self):
        """Test _handle_trace_results with traces."""
        traces = [
            {"path": "module1.__design__", "overrides_previous": False},
            {"path": "module2.__design__", "overrides_previous": True},
        ]

        with patch("builtins.print") as mock_print:
            result = _handle_trace_results("mykey", traces, True)

            assert result == 0
            assert mock_print.call_count >= 3

    def test_trace_key_no_key_name(self):
        """Test trace_key with no key name."""
        with patch("pinjected.main_impl._print_trace_key_error") as mock_error:
            result = trace_key("")

            assert result == 1
            mock_error.assert_called_once()

    def test_trace_key_success(self):
        """Test trace_key success."""
        with (
            patch("asyncio.run") as mock_run,
            patch("pinjected.main_impl._handle_trace_results") as mock_handle,
            patch("pinjected.pinjected_logging.logger"),
        ):
            mock_run.return_value = (["trace1"], True)

            result = trace_key("mykey", "my.module")

            assert result == mock_handle.return_value
            mock_handle.assert_called_once_with("mykey", ["trace1"], True)

    def test_trace_key_exception(self):
        """Test trace_key with exception."""
        with patch("asyncio.run") as mock_run, patch("builtins.print") as mock_print:
            mock_run.side_effect = RuntimeError("Test error")

            result = trace_key("mykey")

            assert result == 1
            assert "Error: Test error" in mock_print.call_args[0][0]


class TestPinjectedCLI:
    """Test PinjectedCLI class."""

    def test_init(self):
        """Test PinjectedCLI initialization."""
        cli = PinjectedCLI()

        assert cli.run == run
        assert cli.resolve == run  # Alias
        assert cli.check_config == check_config
        assert cli.json_graph == json_graph
        assert cli.describe == describe
        assert cli.describe_json == describe_json
        assert cli.list == list
        assert cli.trace_key == trace_key
        assert hasattr(cli, "create_overloads")


class TestRunFunction:
    """Test run function."""

    @patch("asyncio.run")
    def test_run_simple(self, mock_asyncio_run):
        """Test simple run."""
        with (
            patch("pinjected.main_impl.disable_internal_logging"),
            patch("pinjected.main_impl.a_get_run_context") as mock_get_ctx,
            patch("pinjected.main_impl.a_run_with_notify") as mock_notify,
        ):
            # Setup mocks
            mock_ctx = AsyncMock()
            mock_ctx.add_overrides.return_value = mock_ctx
            mock_ctx.a_run_with_clean_stacktrace = AsyncMock(return_value="result")
            mock_get_ctx.return_value = mock_ctx
            mock_notify.return_value = "result"

            # Configure asyncio.run to return a result directly
            mock_asyncio_run.return_value = "result"

            # Run
            run("my.var", "my.design")

            # Verify
            assert mock_asyncio_run.called

    @patch("asyncio.run")
    def test_run_with_base64_json(self, mock_asyncio_run):
        """Test run with base64 encoded JSON."""
        data = {
            "var_path": "my.var",
            "design_path": "my.design",
            "overrides": "my.overrides",
            "meta_context_path": "/path/to/meta",
            "extra": "param",
        }
        encoded = base64.b64encode(json.dumps(data).encode()).decode()

        with (
            patch("pinjected.main_impl.disable_internal_logging"),
            patch("pinjected.main_impl.a_get_run_context"),
            patch("pinjected.main_impl.a_run_with_notify"),
        ):
            # Run
            run(base64_encoded_json=encoded)

            # Verify asyncio.run was called
            assert mock_asyncio_run.called


class TestCallFunction:
    """Test call function."""

    @patch("asyncio.run")
    def test_call_simple(self, mock_asyncio_run):
        """Test simple call."""
        with patch("pinjected.main_impl.a_get_run_context") as mock_get_ctx:
            # Setup mocks
            mock_ctx = Mock()
            mock_ctx.add_design.return_value = mock_ctx
            mock_func = Mock(return_value="sync_result")
            mock_ctx.a_run = AsyncMock(return_value=mock_func)

            # a_get_run_context is async, so it should return the context when awaited
            async def return_ctx(*args, **kwargs):
                return mock_ctx

            mock_get_ctx.side_effect = return_ctx

            # Configure asyncio.run
            async def run_coro(coro):
                return await coro

            mock_asyncio_run.side_effect = (
                lambda coro: asyncio.get_event_loop().run_until_complete(run_coro(coro))
            )

            # Run
            result = call("my.var", "my.design")

            # Result should be a callable
            assert callable(result)

    @patch("asyncio.run")
    def test_call_with_call_kwargs(self, mock_asyncio_run):
        """Test call with call_kwargs_base64_json."""
        call_kwargs = {"arg1": "value1", "arg2": 42}
        encoded_kwargs = base64.b64encode(json.dumps(call_kwargs).encode()).decode()

        with (
            patch("pinjected.main_impl.a_get_run_context") as mock_get_ctx,
            patch("pinjected.pinjected_logging.logger"),
        ):
            # Setup mocks
            mock_ctx = Mock()
            mock_ctx.add_design.return_value = mock_ctx
            mock_func = Mock(return_value="func_result")
            mock_ctx.a_run = AsyncMock(return_value=mock_func)

            # a_get_run_context is async, so it should return the context when awaited
            async def return_ctx(*args, **kwargs):
                return mock_ctx

            mock_get_ctx.side_effect = return_ctx

            # Configure asyncio.run
            async def run_coro(coro):
                return await coro

            mock_asyncio_run.side_effect = (
                lambda coro: asyncio.get_event_loop().run_until_complete(run_coro(coro))
            )

            # Run
            call("my.var", call_kwargs_base64_json=encoded_kwargs)

            # Verify function was called with kwargs
            mock_func.assert_called_once_with(**call_kwargs)


class TestMainFunction:
    """Test main function."""

    def test_main_success(self):
        """Test main function normal execution."""
        with patch("fire.Fire") as mock_fire:
            result = main()

            mock_fire.assert_called_once()
            assert isinstance(result, PinjectedCLI)

    def test_main_with_dependency_resolution_error(self):
        """Test main with DependencyResolutionError."""
        from pinjected.exceptions import DependencyResolutionError
        from pinjected.run_helpers.run_injected import PinjectedRunFailure

        with patch("fire.Fire") as mock_fire:
            error = DependencyResolutionError("Test error")
            failure = PinjectedRunFailure("Run failed")
            failure.__cause__ = error
            mock_fire.side_effect = failure

            with pytest.raises(PinjectedRunDependencyResolutionFailure):
                main()

    def test_main_with_validation_error(self):
        """Test main with DependencyValidationError."""
        from pinjected.exceptions import DependencyValidationError
        from pinjected.run_helpers.run_injected import PinjectedRunFailure

        with patch("fire.Fire") as mock_fire:
            error = DependencyValidationError("Validation failed", cause=None)
            failure = PinjectedRunFailure("Run failed")
            failure.__cause__ = error
            mock_fire.side_effect = failure

            with pytest.raises(
                PinjectedRunDependencyResolutionFailure,
                match="Dependency validation failed",
            ):
                main()

    def test_main_with_other_exception(self):
        """Test main with other exception."""
        with patch("fire.Fire") as mock_fire:
            mock_fire.side_effect = RuntimeError("Other error")

            with pytest.raises(RuntimeError, match="Other error"):
                main()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
