"""Simple tests for helpers.py module."""

import pytest
from unittest.mock import patch, Mock
from pathlib import Path
from dataclasses import is_dataclass

from pinjected.helpers import (
    inspect_and_make_configurations,
    RunnableSpec,
    get_design_path_from_var_path,
    find_default_design_path,
    find_default_working_dir,
)
from pinjected.module_var_path import ModuleVarPath


class TestInspectAndMakeConfigurations:
    """Test the inspect_and_make_configurations function."""

    def test_inspect_and_make_configurations_is_injected(self):
        """Test that inspect_and_make_configurations is injected."""
        from pinjected.di.partially_injected import Partial

        assert isinstance(inspect_and_make_configurations, Partial)

    @patch("pinjected.helpers.get_runnables")
    def test_inspect_and_make_configurations_function(self, mock_get_runnables):
        """Test the inspect_and_make_configurations function logic."""
        # Get the underlying function
        func = inspect_and_make_configurations.src_function

        # Setup mocks
        mock_logger = Mock()
        mock_injected_to_idea_configs = Mock()
        mock_config = Mock()
        mock_config.configs = {"test": "config"}
        mock_injected_to_idea_configs.return_value = mock_config

        from pinjected.module_inspector import ModuleVarSpec

        mock_spec = Mock(spec=ModuleVarSpec)
        mock_get_runnables.return_value = [mock_spec]

        # Call function with positional-only arguments before /
        result = func(
            mock_injected_to_idea_configs,
            mock_logger,
            module_path=Path("/test/module.py"),
        )

        # Verify
        mock_get_runnables.assert_called_once_with(Path("/test/module.py"))
        mock_logger.info.assert_called()
        assert result.configs == {"test": "config"}


class TestRunnableSpec:
    """Test the RunnableSpec dataclass."""

    def test_runnable_spec_is_dataclass(self):
        """Test that RunnableSpec is a dataclass."""
        assert is_dataclass(RunnableSpec)

    def test_runnable_spec_creation(self):
        """Test creating RunnableSpec with valid paths."""
        tgt_path = ModuleVarPath("module.target_var")
        design_path = ModuleVarPath("module.design_var")

        spec = RunnableSpec(tgt_path=tgt_path, design_path=design_path)

        assert spec.tgt_path == tgt_path
        assert spec.design_path == design_path

    def test_runnable_spec_default_design_path(self):
        """Test RunnableSpec with default design path."""
        tgt_path = ModuleVarPath("module.target_var")

        spec = RunnableSpec(tgt_path=tgt_path)

        assert spec.tgt_path == tgt_path
        assert spec.design_path.var_name == "EmptyDesign"

    def test_runnable_spec_properties(self):
        """Test RunnableSpec properties."""
        spec = RunnableSpec(
            tgt_path=ModuleVarPath("module.my_target"),
            design_path=ModuleVarPath("module.my_design"),
        )

        assert spec.target_name == "my_target"
        assert spec.design_name == "my_design"

    def test_runnable_spec_type_validation(self):
        """Test RunnableSpec type validation in __post_init__."""
        # Should raise AssertionError for non-ModuleVarPath
        with pytest.raises(AssertionError):
            RunnableSpec(tgt_path="not_a_module_var_path")


class TestGetDesignPathFromVarPath:
    """Test the get_design_path_from_var_path function."""

    def test_get_design_path_from_var_path_none(self):
        """Test get_design_path_from_var_path with None input."""
        with pytest.raises(ValueError) as exc_info:
            get_design_path_from_var_path(None)

        assert "Variable path cannot be None" in str(exc_info.value)

    @patch("pinjected.helpers.importlib.import_module")
    @patch("pinjected.helpers.find_default_design_paths")
    def test_get_design_path_from_var_path_success(self, mock_find_paths, mock_import):
        """Test successful design path retrieval."""
        # Setup mocks
        mock_module = Mock()
        mock_module.__file__ = "/path/to/module.py"
        mock_import.return_value = mock_module
        mock_find_paths.return_value = ["/path/to/design"]

        result = get_design_path_from_var_path("my.module.path.var_name")

        assert result == "/path/to/design"
        mock_import.assert_called_once_with("my.module.path")
        mock_find_paths.assert_called_once_with("/path/to/module.py", None)

    @patch("pinjected.helpers.importlib.import_module")
    def test_get_design_path_from_var_path_import_error(self, mock_import):
        """Test get_design_path_from_var_path with import error."""
        mock_import.side_effect = ImportError("Module not found")

        with pytest.raises(ImportError) as exc_info:
            get_design_path_from_var_path("nonexistent.module.var")

        assert "Could not import module path" in str(exc_info.value)


class TestFindHelperFunctions:
    """Test the find_* helper functions."""

    @patch("pinjected.helpers.find_module_attr")
    def test_find_default_design_path(self, mock_find_attr):
        """Test find_default_design_path function."""
        mock_find_attr.return_value = "/default/design/path"

        result = find_default_design_path("/path/to/file.py")

        assert result == "/default/design/path"
        mock_find_attr.assert_called_once_with(
            "/path/to/file.py", "__default_design_path__"
        )

    @patch("pinjected.helpers.find_module_attr")
    def test_find_default_working_dir(self, mock_find_attr):
        """Test find_default_working_dir function."""
        mock_find_attr.return_value = "/working/dir"

        result = find_default_working_dir("/path/to/file.py")

        assert result == "/working/dir"
        mock_find_attr.assert_called_once_with(
            "/path/to/file.py", "__default_working_dir__"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
