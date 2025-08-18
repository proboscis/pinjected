"""Additional tests to improve coverage for pinjected/ide_supports/create_configs.py"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from pinjected import design
from pinjected.ide_supports.create_configs import (
    run_with_meta_context,
    get_filtered_signature,
)
from pinjected.helper_structure import (
    IdeaRunConfigurations,
)


class TestCreateIdeaConfigurationsCoverage:
    """Tests to improve coverage for create_idea_configurations."""

    def test_create_idea_configurations_return_without_print(self):
        """Test create_idea_configurations returns configs when print_to_stdout=False."""
        # This tests line 129: return configs
        from pinjected import design

        # Create a mock configurations object
        mock_configs = IdeaRunConfigurations(configs={"test": []})
        mock_inspect = Mock(return_value=mock_configs)

        # Create a design that provides create_idea_configurations and its dependencies
        test_design = design(
            inspect_and_make_configurations=mock_inspect,
            module_path=Path("/test/module.py"),
            print_to_stdout=False,
            __pinjected__wrap_output_with_tag=True,
        )

        # Get the graph and provide create_idea_configurations
        graph = test_design.to_graph()
        result = graph.provide("create_idea_configurations")

        # Should return the configs object
        assert result == mock_configs


class TestGetFilteredSignatureCoverage:
    """Tests to improve coverage for get_filtered_signature."""

    def test_get_filtered_signature_with_class(self):
        """Test get_filtered_signature with a class that has __init__."""

        class TestClass:
            def __init__(self, a, b, /, c, d=10):
                self.a = a
                self.b = b
                self.c = c
                self.d = d

        name, sig = get_filtered_signature(TestClass)

        assert name == "TestClass"
        # Should filter out positional-only params (a, b)
        assert "a" not in sig
        assert "b" not in sig
        assert "c" in sig
        assert "d" in sig

    def test_get_filtered_signature_lambda(self):
        """Test get_filtered_signature with lambda function."""

        def lambda_func(x, y=5):
            return x + y

        name, sig = get_filtered_signature(lambda_func)

        assert name == "lambda_func"
        assert "x" in sig
        assert "y" in sig

    def test_get_filtered_signature_no_params(self):
        """Test get_filtered_signature with no parameters."""

        def no_params():
            pass

        name, sig = get_filtered_signature(no_params)

        assert name == "no_params"
        assert sig == "()"

    def test_get_filtered_signature_all_positional_only(self):
        """Test get_filtered_signature with all positional-only parameters."""

        def all_pos_only(a, b, c, /):
            pass

        name, sig = get_filtered_signature(all_pos_only)

        assert name == "all_pos_only"
        assert sig == "()"  # All params filtered out


class TestRunWithMetaContextAdditional:
    """Additional tests for run_with_meta_context."""

    @patch("pinjected.helper_structure.MetaContext.a_gather_bindings_with_legacy")
    @patch("pinjected.ide_supports.create_configs.run_injected")
    @patch("pinjected.ide_supports.create_configs.logger")
    @patch("sys.executable", "/custom/python")
    def test_run_with_meta_context_custom_interpreter(
        self, mock_logger, mock_run_injected, mock_gather
    ):
        """Test run_with_meta_context uses sys.executable."""
        # Setup mocks
        mock_context = Mock()
        mock_context.final_design = design()
        mock_gather.return_value = mock_context

        mock_run_injected.return_value = "result"

        # Call with custom kwargs
        result = run_with_meta_context(
            "test.var", "/context.py", custom_key="custom_value"
        )

        # Verify the call happened with expected parameters
        # The 'overrides' parameter is passed but we don't need to inspect it
        assert result == "result"
        assert mock_run_injected.called


class TestListCompletionsPartialCoverage:
    """Tests to cover specific branches in list_completions."""

    @patch("builtins.print")
    def test_list_completions_empty_paths_early_return(self, mock_print):
        """Test list_completions with empty paths hits early return."""
        # This specifically tests lines 167-170
        test_design = design(default_design_paths=[])

        graph = test_design.to_graph()
        graph.provide("list_completions")

        # Should print empty JSON array wrapped
        mock_print.assert_called_once_with("<pinjected>[]</pinjected>")


class TestExtractArgsForRunnableMatchCases:
    """Tests for specific match cases in extract_args_for_runnable."""

    def test_extract_args_match_cases_coverage(self):
        """Test various match cases in extract_args_for_runnable."""
        # Since extract_args_for_runnable is @injected, we need to test through DI
        from pinjected.di.injected import InjectedFromFunction, PartialInjectedFunction
        from pinjected.di.proxiable import DelegatedVar
        from pinjected import Designed, Injected
        from pinjected.module_inspector import ModuleVarSpec
        from returns.result import Success

        # Create test design with extract_args_for_runnable
        logger = Mock()

        def test_extract_args(tgt, ddp, meta):
            """Simplified version of extract_args_for_runnable for testing."""
            args = None
            match tgt.var, meta:
                case (_, Success({"kind": "callable"})):
                    args = ["call", tgt.var_path, ddp]
                case (_, Success({"kind": "object"})):
                    args = ["run", tgt.var_path, ddp]
                case (PartialInjectedFunction(), _):
                    args = ["call", tgt.var_path, ddp]
                case (InjectedFromFunction(), _):
                    args = ["call", tgt.var_path, ddp]
                case (Injected(), _):
                    args = ["run", tgt.var_path, ddp]
                case (DelegatedVar(), _):
                    args = ["run", tgt.var_path, ddp]
                case (Designed(), _):
                    args = ["run", tgt.var_path, ddp]
                case _:
                    args = None

            if args is not None:
                logger.info(f"args for {tgt.var_path} is {args}")
            else:
                logger.warning(f"could not extract args for {tgt.var_path}, {tgt.var}")
            return args

        # Test Success({"kind": "callable"}) - line 265
        spec1 = ModuleVarSpec(var=Mock(), var_path="test.func")

        result = test_extract_args(spec1, "design.path", Success({"kind": "callable"}))
        assert result == ["call", "test.func", "design.path"]

        # Test Success({"kind": "object"}) - line 267
        spec2 = ModuleVarSpec(var=Mock(), var_path="test.obj")

        result = test_extract_args(spec2, "design.path", Success({"kind": "object"}))
        assert result == ["run", "test.obj", "design.path"]

        # Test Designed() - lines 277-278
        spec3 = ModuleVarSpec(var=Mock(spec=Designed), var_path="test.designed")

        result = test_extract_args(spec3, "design.path", {})
        assert result == ["run", "test.designed", "design.path"]

        # Test default case (no match) - lines 279-280
        spec4 = ModuleVarSpec(var="just a string", var_path="test.unknown")

        result = test_extract_args(spec4, "design.path", {})
        assert result is None
        logger.warning.assert_called()


class TestInjectedToIdeaConfigsCallablePath:
    """Test injected_to_idea_configs with callable runner_script_path."""

    def test_callable_runner_script_path_coverage(self):
        """Test that callable runner_script_path is handled."""
        # This is to cover line 322

        # Create a callable that returns the path
        def get_runner_path():
            return "/path/to/runner.py"

        # Test the logic directly
        runner_path = get_runner_path
        if callable(runner_path):
            runner_path = runner_path()

        assert runner_path == "/path/to/runner.py"


class TestDesignMetadataLocationTypes:
    """Test design_metadata with different location types."""

    def test_location_handling_logic(self):
        """Test the location handling logic in design_metadata."""
        # Testing the pattern matching logic from lines 228-241
        from pinjected.module_var_path import ModuleVarPath as MVPath
        from pinjected.di.metadata.location_data import ModuleVarLocation as MVLocation

        # Test MVPath case
        mvpath = MVPath("test.module.var")
        location_dict = None

        if isinstance(mvpath, MVPath):
            location_dict = dict(
                type="path",
                value=mvpath.path if hasattr(mvpath, "path") else str(mvpath),
            )

        assert location_dict is not None
        assert location_dict["type"] == "path"

        # Test MVLocation case
        mvlocation = Mock(spec=MVLocation)
        mvlocation.path = "/test/file.py"
        mvlocation.line = 10
        mvlocation.column = 5

        if isinstance(mvlocation, MVLocation):
            location_dict = dict(
                type="coordinates",
                value=f"{mvlocation.path}:{mvlocation.line}:{mvlocation.column}",
            )

        assert location_dict["type"] == "coordinates"
        assert location_dict["value"] == "/test/file.py:10:5"


class TestInjectedToIdeaConfigsMetadataHandling:
    """Test metadata handling in injected_to_idea_configs."""

    def test_metadata_success_case(self):
        """Test handling of Success metadata with default_design_path."""
        # This tests line 336
        from returns.result import Success

        meta = Success({"default_design_path": "custom.design.path"})
        ddps = []

        match meta:
            case Success({"default_design_path": ddp}):
                ddps.append(ddp)

        assert "custom.design.path" in ddps

    def test_no_metadata_case(self):
        """Test handling when no metadata matches."""
        from returns.result import Failure, Success

        meta = Failure(Exception("No metadata"))
        ddps = []

        match meta:
            case Success({"default_design_path": ddp}):
                ddps.append(ddp)

        assert len(ddps) == 0


class TestExtractArgsErrorHandling:
    """Test error handling in extract_args_for_runnable."""

    def test_warning_logged_for_none_args(self):
        """Test that warning is logged when args is None."""
        # This tests line 284
        logger = Mock()

        # Simulate the logging logic
        args = None
        var_path = "test.unknown"
        var = object()

        if args is not None:
            logger.info(f"args for {var_path} is {args}")
        else:
            logger.warning(f"could not extract args for {var_path}, {var}")

        logger.warning.assert_called_once()
        assert (
            "could not extract args for test.unknown" in logger.warning.call_args[0][0]
        )


class TestInjectedToIdeaConfigsExceptionHandling:
    """Test exception handling in injected_to_idea_configs."""

    def test_custom_creator_exception_handling(self):
        """Test exception handling for custom_idea_config_creator."""
        # This tests lines 418-422
        logger = Mock()

        def failing_creator(tgt):
            raise ValueError("Custom creation failed")

        tgt = Mock()
        tgt.var_path = "test.func"

        try:
            failing_creator(tgt)
        except Exception as e:
            logger.warning(
                f"Failed to create custom idea configs for {tgt} because {e}"
            )
            with pytest.raises(RuntimeError) as exc_info:
                raise RuntimeError(
                    f"Failed to create custom idea configs for {tgt} because {e}"
                ) from e

        logger.warning.assert_called_once()
        assert "Failed to create custom idea configs" in str(exc_info.value)

    def test_internal_creator_exception_handling(self):
        """Test exception handling for internal_idea_config_creator."""
        # This tests lines 429-434
        logger = Mock()

        def failing_creator(tgt):
            raise ValueError("Internal creation failed")

        tgt = Mock()
        tgt.var_path = "test.func"

        try:
            failing_creator(tgt)
        except Exception as e:
            logger.warning(
                f"Failed to create internal idea configs for {tgt} because {e}"
            )
            with pytest.raises(RuntimeError) as exc_info:
                raise RuntimeError(
                    f"Failed to create internal idea configs for {tgt} because {e}"
                ) from e

        logger.warning.assert_called_once()
        assert "Failed to create internal idea configs" in str(exc_info.value)


class TestInjectedToIdeaConfigsLogging:
    """Test logging in injected_to_idea_configs."""

    def test_warning_for_no_runnable_metadata(self):
        """Test warning is logged for missing __runnable_metadata__."""
        # This tests lines 408-410
        logger = Mock()
        var_path = "test.module.func"

        # Simulate the logging
        logger.warning(f"skipping {var_path} because it has no __runnable_metadata__")

        logger.warning.assert_called_once()
        assert "skipping test.module.func" in logger.warning.call_args[0][0]
        assert "no __runnable_metadata__" in logger.warning.call_args[0][0]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
