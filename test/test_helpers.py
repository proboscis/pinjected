"""Comprehensive tests for pinjected.helpers module to improve coverage."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch


from pinjected.helpers import (
    RunnableSpec,
    get_design_path_from_var_path,
    find_default_design_path,
    find_default_working_dir,
    find_default_design_paths,
    find_module_attr,
    IdeaRunConfigurations,
)
from pinjected.module_var_path import ModuleVarPath
from pinjected.module_inspector import ModuleVarSpec


class TestRunnableSpec:
    """Tests for RunnableSpec dataclass."""

    def test_runnable_spec_creation_basic(self):
        """Test creating RunnableSpec with target path only."""
        tgt_path = ModuleVarPath("test.module.function")
        spec = RunnableSpec(tgt_path=tgt_path)

        assert spec.tgt_path == tgt_path
        assert spec.design_path.path == "pinjected.di.util.EmptyDesign"

    def test_runnable_spec_creation_with_design(self):
        """Test creating RunnableSpec with both paths."""
        tgt_path = ModuleVarPath("test.module.function")
        design_path = ModuleVarPath("test.design.MyDesign")

        spec = RunnableSpec(tgt_path=tgt_path, design_path=design_path)

        assert spec.tgt_path == tgt_path
        assert spec.design_path == design_path

    def test_runnable_spec_invalid_tgt_path(self):
        """Test RunnableSpec with invalid target path type."""
        with pytest.raises(AssertionError):
            RunnableSpec(tgt_path="not a ModuleVarPath")

    def test_runnable_spec_invalid_design_path(self):
        """Test RunnableSpec with invalid design path type."""
        tgt_path = ModuleVarPath("test.module.function")

        with pytest.raises(AssertionError):
            RunnableSpec(tgt_path=tgt_path, design_path="not a ModuleVarPath")

    def test_target_name_property(self):
        """Test target_name property."""
        tgt_path = ModuleVarPath("test.module.my_function")
        spec = RunnableSpec(tgt_path=tgt_path)

        assert spec.target_name == "my_function"

    def test_design_name_property(self):
        """Test design_name property."""
        tgt_path = ModuleVarPath("test.module.function")
        design_path = ModuleVarPath("test.design.MyDesign")
        spec = RunnableSpec(tgt_path=tgt_path, design_path=design_path)

        assert spec.design_name == "MyDesign"


class TestGetDesignPathFromVarPath:
    """Tests for get_design_path_from_var_path function."""

    def test_get_design_path_none_input(self):
        """Test with None input."""
        with pytest.raises(ValueError) as exc_info:
            get_design_path_from_var_path(None)

        assert "Variable path cannot be None" in str(exc_info.value)

    @patch("pinjected.helpers.importlib.import_module")
    @patch("pinjected.helpers.find_default_design_paths")
    @patch("pinjected.pinjected_logging.logger")
    def test_get_design_path_success(self, mock_logger, mock_find_paths, mock_import):
        """Test successful design path retrieval."""
        # Mock module with __file__ attribute
        mock_module = Mock()
        mock_module.__file__ = "/path/to/module.py"
        mock_import.return_value = mock_module

        # Mock finding design paths
        mock_find_paths.return_value = [
            "test.design.MyDesign",
            "test.design.OtherDesign",
        ]

        result = get_design_path_from_var_path("test.module.function")

        assert result == "test.design.MyDesign"
        mock_import.assert_called_once_with("test.module")
        mock_find_paths.assert_called_once_with("/path/to/module.py", None)

    @patch("pinjected.helpers.importlib.import_module")
    @patch("pinjected.helpers.find_default_design_paths")
    @patch("pinjected.pinjected_logging.logger")
    def test_get_design_path_no_paths_found(
        self, mock_logger, mock_find_paths, mock_import
    ):
        """Test when no design paths are found."""
        mock_module = Mock()
        mock_module.__file__ = "/path/to/module.py"
        mock_import.return_value = mock_module

        mock_find_paths.return_value = []

        with pytest.raises(ValueError) as exc_info:
            get_design_path_from_var_path("test.module.function")

        assert "No default design paths found" in str(exc_info.value)

    @patch("pinjected.helpers.importlib.import_module")
    @patch("pinjected.pinjected_logging.logger")
    def test_get_design_path_import_error(self, mock_logger, mock_import):
        """Test when module import fails."""
        mock_import.side_effect = ImportError("Module not found")

        with pytest.raises(ImportError) as exc_info:
            get_design_path_from_var_path("test.module.function")

        assert "Could not import module path" in str(exc_info.value)
        mock_logger.warning.assert_called_once()


class TestFindDefaultDesignPath:
    """Tests for find_default_design_path function."""

    @patch("pinjected.helpers.find_module_attr")
    @patch("pinjected.pinjected_logging.logger")
    def test_find_default_design_path(self, mock_logger, mock_find_attr):
        """Test finding default design path."""
        mock_find_attr.return_value = "test.design.DefaultDesign"

        result = find_default_design_path("/path/to/file.py")

        assert result == "test.design.DefaultDesign"
        mock_find_attr.assert_called_once_with(
            "/path/to/file.py", "__default_design_path__"
        )
        mock_logger.info.assert_called_once()

    @patch("pinjected.helpers.find_module_attr")
    @patch("pinjected.pinjected_logging.logger")
    def test_find_default_design_path_none(self, mock_logger, mock_find_attr):
        """Test when no default design path is found."""
        mock_find_attr.return_value = None

        result = find_default_design_path("/path/to/file.py")

        assert result is None


class TestFindDefaultWorkingDir:
    """Tests for find_default_working_dir function."""

    @patch("pinjected.helpers.find_module_attr")
    @patch("pinjected.pinjected_logging.logger")
    def test_find_default_working_dir(self, mock_logger, mock_find_attr):
        """Test finding default working directory."""
        mock_find_attr.return_value = "/path/to/workdir"

        result = find_default_working_dir("/path/to/file.py")

        assert result == "/path/to/workdir"
        mock_find_attr.assert_called_once_with(
            "/path/to/file.py", "__default_working_dir__"
        )
        mock_logger.info.assert_called_once()


class TestFindDefaultDesignPaths:
    """Tests for find_default_design_paths function."""

    @patch("pinjected.helpers.find_module_attr")
    @patch("pinjected.helpers.find_default_design_path")
    @patch("pinjected.pinjected_logging.logger")
    def test_find_default_design_paths_all_sources(
        self, mock_logger, mock_find_path, mock_find_attr
    ):
        """Test with all sources providing paths."""
        # Mock __default_design_paths__
        mock_find_attr.return_value = ["design1", "design2"]

        # Mock __default_design_path__
        mock_find_path.return_value = "design3"

        result = find_default_design_paths("/path/to/module.py", "design4")

        # Should combine all sources
        assert result == ["design1", "design2", "design4"]

    @patch("pinjected.helpers.find_module_attr")
    @patch("pinjected.helpers.find_default_design_path")
    @patch("pinjected.pinjected_logging.logger")
    def test_find_default_design_paths_no_attr_paths(
        self, mock_logger, mock_find_path, mock_find_attr
    ):
        """Test when __default_design_paths__ is not found."""
        # Mock no __default_design_paths__
        mock_find_attr.return_value = None

        # Mock __default_design_path__
        mock_find_path.return_value = "design1"

        result = find_default_design_paths("/path/to/module.py", None)

        assert result == ["design1"]

    @patch("pinjected.helpers.find_module_attr")
    @patch("pinjected.helpers.find_default_design_path")
    @patch("pinjected.pinjected_logging.logger")
    def test_find_default_design_paths_no_single_path(
        self, mock_logger, mock_find_path, mock_find_attr
    ):
        """Test when single design path is not found."""
        # Mock __default_design_paths__
        mock_find_attr.return_value = ["design1", "design2"]

        # Mock no __default_design_path__
        mock_find_path.return_value = None

        result = find_default_design_paths("/path/to/module.py", None)

        assert result == ["design1", "design2"]

    @patch("pinjected.helpers.find_module_attr")
    @patch("pinjected.helpers.find_default_design_path")
    @patch("pinjected.pinjected_logging.logger")
    def test_find_default_design_paths_empty(
        self, mock_logger, mock_find_path, mock_find_attr
    ):
        """Test when no paths are found from any source."""
        mock_find_attr.return_value = None
        mock_find_path.return_value = None

        result = find_default_design_paths("/path/to/module.py", None)

        assert result == []


class TestFindModuleAttr:
    """Tests for find_module_attr function."""

    @patch("pinjected.helpers.walk_module_attr")
    def test_find_module_attr_found(self, mock_walk):
        """Test finding module attribute."""
        mock_item = Mock()
        mock_item.var = "test_value"
        mock_walk.return_value = [
            mock_item,
            Mock(),
        ]  # Multiple items, should return first

        result = find_module_attr("/path/to/file.py", "test_attr")

        assert result == "test_value"
        mock_walk.assert_called_once_with(Path("/path/to/file.py"), "test_attr", None)

    @patch("pinjected.helpers.walk_module_attr")
    def test_find_module_attr_not_found(self, mock_walk):
        """Test when attribute is not found."""
        mock_walk.return_value = []  # Empty iterator

        result = find_module_attr("/path/to/file.py", "test_attr")

        assert result is None

    @patch("pinjected.helpers.walk_module_attr")
    def test_find_module_attr_with_root_module(self, mock_walk):
        """Test with root module path specified."""
        mock_item = Mock()
        mock_item.var = "test_value"
        mock_walk.return_value = [mock_item]

        result = find_module_attr("/path/to/file.py", "test_attr", "/root/module")

        assert result == "test_value"
        mock_walk.assert_called_once_with(
            Path("/path/to/file.py"), "test_attr", "/root/module"
        )


class TestIntegration:
    """Integration tests for helpers module."""

    def test_runnable_spec_full_workflow(self):
        """Test full workflow with RunnableSpec."""
        # Create specs
        tgt_path = ModuleVarPath("my.module.test_function")
        design_path = ModuleVarPath("my.design.TestDesign")

        spec = RunnableSpec(tgt_path=tgt_path, design_path=design_path)

        # Verify all properties work correctly
        assert spec.target_name == "test_function"
        assert spec.design_name == "TestDesign"
        assert isinstance(spec.tgt_path, ModuleVarPath)
        assert isinstance(spec.design_path, ModuleVarPath)


class TestInspectAndMakeConfigurations:
    """Tests for inspect_and_make_configurations function."""

    @patch("pinjected.helpers.get_runnables")
    def test_inspect_and_make_configurations(self, mock_get_runnables, tmp_path):
        """Test inspect_and_make_configurations with mocked dependencies."""
        # Create test module file
        test_module = tmp_path / "test_module.py"
        test_module.touch()

        # Mock get_runnables to return a ModuleVarSpec
        mock_spec = ModuleVarSpec(var="test_var", var_path="test.module.var")
        mock_get_runnables.return_value = [mock_spec]

        # Mock dependencies
        mock_logger = Mock()
        mock_injected_to_idea_configs = Mock()

        # Mock the return value for injected_to_idea_configs
        mock_config_result = Mock()
        mock_config_result.configs = {"test_config": "config_value"}
        mock_injected_to_idea_configs.return_value = mock_config_result

        # Since inspect_and_make_configurations is an @injected function,
        # we need to test it through dependency injection
        from pinjected import design
        from pinjected.v2.async_resolver import AsyncResolver
        from pinjected.helpers import inspect_and_make_configurations

        # Create a design with our mocked dependencies
        test_design = design(
            injected_to_idea_configs=mock_injected_to_idea_configs, logger=mock_logger
        )

        # Use resolver to provide the function with dependencies
        resolver = AsyncResolver(test_design)
        blocking = resolver.to_blocking()

        # Get the function with dependencies injected
        inspect_func = blocking.provide(inspect_and_make_configurations)

        # Call the function with just the module_path
        result = inspect_func(test_module)

        # Verify the result
        assert isinstance(result, IdeaRunConfigurations)
        assert "test_config" in result.configs

        # Verify logger was called
        assert mock_logger.info.call_count >= 2

        # Verify get_runnables was called with the correct path
        mock_get_runnables.assert_called_once_with(test_module)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
