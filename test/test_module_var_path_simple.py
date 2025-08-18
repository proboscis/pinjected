"""Simple tests for module_var_path.py module."""

import pytest
from unittest.mock import patch, Mock
from pathlib import Path
from dataclasses import is_dataclass

from pinjected.module_var_path import ModuleVarPath


class TestModuleVarPath:
    """Test the ModuleVarPath dataclass."""

    def test_module_var_path_is_dataclass(self):
        """Test that ModuleVarPath is a dataclass."""
        assert is_dataclass(ModuleVarPath)

    def test_module_var_path_is_frozen(self):
        """Test that ModuleVarPath is frozen."""
        mvp = ModuleVarPath(path="module.variable")

        # Should not be able to modify
        with pytest.raises(AttributeError):
            mvp.path = "other.path"

    def test_module_var_path_creation(self):
        """Test creating ModuleVarPath instance."""
        mvp = ModuleVarPath(path="my.module.path.variable")

        assert mvp.path == "my.module.path.variable"

    def test_module_var_path_post_init_validation(self):
        """Test that post_init validates module and var names."""
        # Valid path should work
        mvp = ModuleVarPath(path="module.var")
        assert mvp.module_name == "module"
        assert mvp.var_name == "var"

        # Single component path should also work (module_name == var_name)
        mvp2 = ModuleVarPath(path="single")
        assert mvp2.module_name == "single"
        assert mvp2.var_name == "single"

    def test_module_name_property(self):
        """Test module_name property extraction."""
        # Multi-level path
        mvp1 = ModuleVarPath(path="package.subpackage.module.variable")
        assert mvp1.module_name == "package.subpackage.module"

        # Two-level path
        mvp2 = ModuleVarPath(path="module.variable")
        assert mvp2.module_name == "module"

        # Single-level path
        mvp3 = ModuleVarPath(path="variable")
        assert mvp3.module_name == "variable"

    def test_var_name_property(self):
        """Test var_name property extraction."""
        mvp1 = ModuleVarPath(path="package.module.MyClass")
        assert mvp1.var_name == "MyClass"

        mvp2 = ModuleVarPath(path="module.function_name")
        assert mvp2.var_name == "function_name"

        mvp3 = ModuleVarPath(path="single")
        assert mvp3.var_name == "single"

    def test_to_import_line(self):
        """Test to_import_line method."""
        mvp1 = ModuleVarPath(path="package.module.MyClass")
        assert mvp1.to_import_line() == "from package.module import MyClass"

        mvp2 = ModuleVarPath(path="os.path")
        assert mvp2.to_import_line() == "from os import path"

        # Single component results in "from single import single"
        mvp3 = ModuleVarPath(path="single")
        assert mvp3.to_import_line() == "from single import single"

    @patch("pinjected.module_var_path.load_variable_by_module_path")
    def test_load_method(self, mock_load):
        """Test load method calls load_variable_by_module_path."""
        mock_load.return_value = "loaded_value"

        mvp = ModuleVarPath(path="module.variable")
        result = mvp.load()

        assert result == "loaded_value"
        mock_load.assert_called_once_with("module.variable")

    @patch("pinjected.module_var_path.sys.modules")
    def test_module_file_path_already_imported(self, mock_modules):
        """Test module_file_path when module is already imported."""
        mock_module = Mock()
        mock_module.__file__ = "/path/to/module.py"
        mock_modules.__getitem__.return_value = mock_module
        mock_modules.__contains__.return_value = True

        mvp = ModuleVarPath(path="already.imported.variable")
        file_path = mvp.module_file_path

        assert file_path == Path("/path/to/module.py")
        assert mock_modules.__getitem__.called

    @patch("pinjected.module_var_path.sys.modules")
    @patch("builtins.__import__")
    def test_module_file_path_not_imported(self, mock_import, mock_modules):
        """Test module_file_path when module needs to be imported."""
        mock_module = Mock()
        mock_module.__file__ = "/path/to/new/module.py"

        # First check returns False, after import returns module
        mock_modules.__contains__.return_value = False
        mock_modules.__getitem__.return_value = mock_module

        mvp = ModuleVarPath(path="new.module.variable")
        file_path = mvp.module_file_path

        assert file_path == Path("/path/to/new/module.py")
        mock_import.assert_called_once_with("new.module")

    def test_module_var_path_docstring(self):
        """Test ModuleVarPath has proper docstring."""
        assert ModuleVarPath.__doc__ is not None
        assert "path" in ModuleVarPath.__doc__
        assert "variable" in ModuleVarPath.__doc__


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
