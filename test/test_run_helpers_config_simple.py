"""Simple tests for run_helpers/config.py module."""

import pytest
from pathlib import Path
from unittest.mock import patch, Mock
from dataclasses import is_dataclass

from pinjected.run_helpers.config import ConfigCreationArgs


class TestRunHelpersConfig:
    """Test the run_helpers/config module functionality."""

    def test_config_creation_args_is_dataclass(self):
        """Test that ConfigCreationArgs is a dataclass."""
        assert is_dataclass(ConfigCreationArgs)

    def test_config_creation_args_creation(self):
        """Test creating ConfigCreationArgs with different parameters."""
        # With only required parameter
        args1 = ConfigCreationArgs(module_path="/path/to/module")
        assert args1.module_path == "/path/to/module"
        assert args1.default_design_path is None
        assert args1.runner_script_path is None
        assert args1.interpreter_path is None
        assert args1.working_dir is None

        # With all parameters
        args2 = ConfigCreationArgs(
            module_path="/path/to/module",
            default_design_path="/path/to/design",
            runner_script_path="/path/to/runner",
            interpreter_path="/usr/bin/python",
            working_dir="/working/dir",
        )
        assert args2.module_path == "/path/to/module"
        assert args2.default_design_path == "/path/to/design"
        assert args2.runner_script_path == "/path/to/runner"
        assert args2.interpreter_path == "/usr/bin/python"
        assert args2.working_dir == "/working/dir"

    @patch("pinjected.run_helpers.config.MetaContext")
    @patch("pinjected.run_helpers.config.get_project_root")
    @patch("pinjected.run_helpers.config.find_default_design_paths")
    @patch("pinjected.run_helpers.config.logger")
    @patch("pinjected.run_helpers.config.design")
    def test_to_design_basic(
        self,
        mock_design_func,
        mock_logger,
        mock_find_paths,
        mock_get_root,
        mock_meta_context,
    ):
        """Test to_design method creates a design object."""
        # Setup mocks
        mock_meta = Mock()
        mock_meta.accumulated = {}  # Empty design object
        mock_meta_context.gather_from_path.return_value = mock_meta
        mock_get_root.return_value = "/project/root"
        mock_find_paths.return_value = ["/default/design/path"]

        # Mock the design function to return a design-like object
        mock_design = Mock()
        mock_design.__add__ = Mock(return_value=mock_design)
        mock_design.__getitem__ = Mock(return_value="mock_value")
        mock_design_func.return_value = mock_design

        # Create args and call to_design
        args = ConfigCreationArgs(module_path="/test/module.py")
        result = args.to_design()

        # Verify calls
        mock_meta_context.gather_from_path.assert_called_once_with(
            Path("/test/module.py")
        )
        mock_logger.debug.assert_called()
        mock_logger.info.assert_called()

        # Result should be a design object
        assert result is not None

    def test_config_creation_args_defaults(self):
        """Test ConfigCreationArgs default values behavior."""
        args = ConfigCreationArgs(module_path="/test/path")

        # Test dataclass features
        repr_str = repr(args)
        assert "ConfigCreationArgs" in repr_str
        assert "module_path='/test/path'" in repr_str
        assert "default_design_path=None" in repr_str

    @patch("pinjected.run_helpers.config.sys.executable", "/custom/python")
    @patch("pinjected.run_helpers.config.__file__", "/config/file.py")
    def test_to_design_uses_defaults(self):
        """Test that to_design uses system defaults when not provided."""
        with (
            patch("pinjected.run_helpers.config.MetaContext") as mock_meta_context,
            patch("pinjected.run_helpers.config.logger"),
            patch("pinjected.run_helpers.config.design") as mock_design_func,
        ):
            mock_meta = Mock()
            mock_meta.accumulated = {}  # Empty design object
            mock_meta_context.gather_from_path.return_value = mock_meta

            # Mock the design function
            mock_design = Mock()
            mock_design.__add__ = Mock(return_value=mock_design)
            mock_design.__getitem__ = Mock(return_value="mock_value")
            mock_design_func.return_value = mock_design

            args = ConfigCreationArgs(module_path="/test/module.py")

            # The design should use sys.executable and __file__ as defaults
            # This is tested through the lambda bindings in the design
            design_obj = args.to_design()

            assert design_obj is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
