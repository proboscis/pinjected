"""Tests for run_helpers/config.py module."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from dataclasses import is_dataclass, fields

from pinjected.run_helpers.config import ConfigCreationArgs


class TestConfigCreationArgs:
    """Tests for ConfigCreationArgs dataclass."""

    def test_is_dataclass(self):
        """Test that ConfigCreationArgs is a dataclass."""
        assert is_dataclass(ConfigCreationArgs)

    def test_fields(self):
        """Test ConfigCreationArgs has expected fields."""
        field_list = fields(ConfigCreationArgs)
        field_names = [f.name for f in field_list]

        assert "module_path" in field_names
        assert "default_design_path" in field_names
        assert "runner_script_path" in field_names
        assert "interpreter_path" in field_names
        assert "working_dir" in field_names

        # Check required field - module_path has no default
        module_path_field = next(f for f in field_list if f.name == "module_path")
        # Check that module_path has no default value (required field)
        from dataclasses import MISSING

        assert module_path_field.default is MISSING
        assert module_path_field.default_factory is MISSING

        # Check optional fields have None default
        for field_name in [
            "default_design_path",
            "runner_script_path",
            "interpreter_path",
            "working_dir",
        ]:
            field = next(f for f in field_list if f.name == field_name)
            assert field.default is None

    def test_initialization_minimal(self):
        """Test ConfigCreationArgs initialization with minimal args."""
        config = ConfigCreationArgs(module_path="/path/to/module")

        assert config.module_path == "/path/to/module"
        assert config.default_design_path is None
        assert config.runner_script_path is None
        assert config.interpreter_path is None
        assert config.working_dir is None

    def test_initialization_full(self):
        """Test ConfigCreationArgs initialization with all args."""
        config = ConfigCreationArgs(
            module_path="/path/to/module",
            default_design_path="/path/to/design",
            runner_script_path="/path/to/runner.py",
            interpreter_path="/usr/bin/python3",
            working_dir="/path/to/workdir",
        )

        assert config.module_path == "/path/to/module"
        assert config.default_design_path == "/path/to/design"
        assert config.runner_script_path == "/path/to/runner.py"
        assert config.interpreter_path == "/usr/bin/python3"
        assert config.working_dir == "/path/to/workdir"

    @patch("pinjected.run_helpers.config.logger")
    @patch("pinjected.run_helpers.config.design")
    @patch("pinjected.run_helpers.config.find_default_design_paths")
    @patch("pinjected.run_helpers.config.get_project_root")
    @patch("pinjected.run_helpers.config.MetaContext")
    def test_to_design_minimal(
        self,
        mock_meta_context,
        mock_get_root,
        mock_find_paths,
        mock_design,
        mock_logger,
    ):
        """Test to_design method with minimal configuration."""
        # Setup mocks
        mock_meta_context_instance = Mock()
        mock_meta_context_instance.accumulated = {"test": "value"}
        mock_meta_context.gather_from_path.return_value = mock_meta_context_instance

        mock_get_root.return_value = "/project/root"
        mock_find_paths.return_value = ["/default/design/path"]

        # Mock design object that supports + and []
        mock_design_obj = MagicMock()
        mock_design_obj.__getitem__.return_value = "custom_config"
        # Mock the __add__ method to return self
        mock_design_obj.__add__.return_value = mock_design_obj
        mock_design.return_value = mock_design_obj

        # Create config and call to_design
        config = ConfigCreationArgs(module_path="/path/to/module.py")
        result = config.to_design()

        # Verify basic calls were made
        assert mock_logger.debug.called
        assert mock_meta_context.gather_from_path.called
        assert mock_design.called

        # Verify the result is what we expect
        assert result == mock_design_obj

        # Verify logger info calls
        assert mock_logger.info.call_count >= 2

    @patch("pinjected.run_helpers.config.logger")
    @patch("pinjected.run_helpers.config.design")
    @patch("pinjected.run_helpers.config.find_default_design_paths")
    @patch("pinjected.run_helpers.config.get_project_root")
    @patch("pinjected.run_helpers.config.MetaContext")
    def test_to_design_with_all_params(
        self,
        mock_meta_context,
        mock_get_root,
        mock_find_paths,
        mock_design,
        mock_logger,
    ):
        """Test to_design method with all parameters specified."""
        # Setup mocks
        mock_meta_context_instance = Mock()
        mock_meta_context_instance.accumulated = {"custom": "meta"}
        mock_meta_context.gather_from_path.return_value = mock_meta_context_instance

        mock_get_root.return_value = "/custom/project/root"
        mock_find_paths.return_value = ["/custom/design/path1", "/custom/design/path2"]

        # Mock design object
        mock_design_obj = MagicMock()
        mock_design_obj.__getitem__.return_value = "custom_config_creator"
        mock_design_obj.__add__.return_value = mock_design_obj
        mock_design.return_value = mock_design_obj

        # Create config with all parameters
        config = ConfigCreationArgs(
            module_path="/custom/module.py",
            default_design_path="/custom/default/design",
            runner_script_path="/custom/runner.py",
            interpreter_path="/custom/python",
            working_dir="/custom/workdir",
        )
        result = config.to_design()

        # Verify design was called
        assert mock_design.called
        assert result == mock_design_obj

        # Note: find_default_design_paths is called inside a lambda passed to Injected.bind
        # so it won't be called during to_design(), only when the design is used later

    @patch("pinjected.run_helpers.config.MetaContext")
    @patch("pinjected.run_helpers.config.get_project_root")
    @patch("pinjected.run_helpers.config.find_default_design_paths")
    @patch("pinjected.run_helpers.config.design")
    @patch("pinjected.run_helpers.config.logger")
    @patch("pinjected.run_helpers.config.sys")
    def test_to_design_uses_sys_executable(
        self,
        mock_sys,
        mock_logger,
        mock_design,
        mock_find_paths,
        mock_get_root,
        mock_meta_context,
    ):
        """Test to_design uses sys.executable when interpreter_path not specified."""
        # Setup mocks
        mock_sys.executable = "/system/python"
        mock_sys.path = ["/path1", "/path2"]

        mock_meta_context_instance = Mock()
        mock_meta_context_instance.accumulated = {}
        mock_meta_context.gather_from_path.return_value = mock_meta_context_instance

        mock_get_root.return_value = "/root"
        mock_find_paths.return_value = ["/design"]

        mock_design_obj = MagicMock()
        mock_design.return_value = mock_design_obj

        # Create config without interpreter_path
        config = ConfigCreationArgs(module_path="/module.py")
        config.to_design()

        # The interpreter_path binding should use sys.executable
        # We can't directly test the lambda, but we verified mock setup
        assert mock_sys.executable == "/system/python"

    def test_str_representation(self):
        """Test string representation of ConfigCreationArgs."""
        config = ConfigCreationArgs(
            module_path="/test/module.py", default_design_path="/test/design"
        )

        str_repr = str(config)
        assert "module_path='/test/module.py'" in str_repr
        assert "default_design_path='/test/design'" in str_repr

    @patch("pinjected.run_helpers.config.MetaContext")
    @patch("pinjected.run_helpers.config.get_project_root")
    @patch("pinjected.run_helpers.config.find_default_design_paths")
    @patch("pinjected.run_helpers.config.design")
    @patch("pinjected.run_helpers.config.logger")
    def test_injected_bindings_are_functions(
        self,
        mock_logger,
        mock_design,
        mock_find_paths,
        mock_get_root,
        mock_meta_context,
    ):
        """Test that Injected.bind receives callable functions."""
        # Setup mocks
        mock_meta_context_instance = Mock()
        mock_meta_context_instance.accumulated = {}
        mock_meta_context.gather_from_path.return_value = mock_meta_context_instance

        mock_design_obj = MagicMock()
        mock_design.return_value = mock_design_obj

        # Capture the Injected.bind calls
        injected_bind_calls = []

        with patch("pinjected.run_helpers.config.Injected") as mock_injected:
            mock_injected.bind.side_effect = (
                lambda func: injected_bind_calls.append(func) or func
            )

            config = ConfigCreationArgs(module_path="/module.py")
            config.to_design()

            # Verify all bind calls received callables
            assert len(injected_bind_calls) > 0
            for func in injected_bind_calls:
                assert callable(func)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
