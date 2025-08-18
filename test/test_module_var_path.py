"""Tests for module_var_path module."""

import pytest
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open, Mock

from pinjected.module_var_path import (
    ModuleVarPath,
    load_variable_by_module_path,
    find_var_or_func_definition_code_in_module,
    find_import_statements_in_module,
    load_variable_from_script,
)
from pinjected.module_inspector import ModuleVarSpec


class TestModuleVarPath:
    """Test ModuleVarPath dataclass."""

    def test_instantiation(self):
        """Test ModuleVarPath instantiation."""
        mvp = ModuleVarPath("module.submodule.variable")
        assert mvp.path == "module.submodule.variable"

    def test_module_name_property(self):
        """Test module_name property."""
        # Multi-level path
        mvp1 = ModuleVarPath("module.submodule.variable")
        assert mvp1.module_name == "module.submodule"

        # Two-level path
        mvp2 = ModuleVarPath("module.variable")
        assert mvp2.module_name == "module"

        # Single level (edge case)
        mvp3 = ModuleVarPath("variable")
        assert mvp3.module_name == "variable"

    def test_var_name_property(self):
        """Test var_name property."""
        mvp1 = ModuleVarPath("module.submodule.variable")
        assert mvp1.var_name == "variable"

        mvp2 = ModuleVarPath("module.var")
        assert mvp2.var_name == "var"

    def test_post_init_validation(self):
        """Test __post_init__ validation."""
        # Should succeed with valid paths
        ModuleVarPath("module.var")
        ModuleVarPath("a.b.c.d")

        # Single name should work too
        ModuleVarPath("module")

    def test_to_import_line(self):
        """Test to_import_line method."""
        mvp = ModuleVarPath("module.submodule.variable")
        assert mvp.to_import_line() == "from module.submodule import variable"

        mvp2 = ModuleVarPath("module.var")
        assert mvp2.to_import_line() == "from module import var"

    def test_load(self):
        """Test load method."""
        mvp = ModuleVarPath("os.path.join")

        # Load should call load_variable_by_module_path
        with patch(
            "pinjected.module_var_path.load_variable_by_module_path"
        ) as mock_load:
            mock_load.return_value = "loaded_value"

            result = mvp.load()

            mock_load.assert_called_once_with("os.path.join")
            assert result == "loaded_value"

    def test_module_file_path_already_imported(self):
        """Test module_file_path when module is already imported."""
        # Use a module that has __file__ attribute
        mvp = ModuleVarPath("pathlib.Path")

        # pathlib should already be in sys.modules
        assert "pathlib" in sys.modules

        path = mvp.module_file_path
        assert isinstance(path, Path)
        assert path.exists()

    def test_module_file_path_not_imported(self):
        """Test module_file_path when module needs importing."""
        # Create a mock module
        mock_module = MagicMock()
        mock_module.__file__ = "/path/to/module.py"

        mvp = ModuleVarPath("test_module.variable")

        with patch.dict("sys.modules", {"test_module": mock_module}):
            path = mvp.module_file_path
            assert path == Path("/path/to/module.py")

    def test_from_local_variable_not_implemented(self):
        """Test from_local_variable raises NotImplementedError."""
        with pytest.raises(NotImplementedError):
            ModuleVarPath.from_local_variable("var_name")

    def test_definition_snippet(self):
        """Test definition_snippet method."""
        mvp = ModuleVarPath("module.var")

        with patch(
            "pinjected.module_var_path.find_var_or_func_definition_code_in_module"
        ) as mock_find:
            mock_find.return_value = "def var(): pass"

            result = mvp.definition_snippet()

            mock_find.assert_called_once_with("module", "var")
            assert result == "def var(): pass"

    def test_depending_import_lines(self):
        """Test depending_import_lines method."""
        mvp = ModuleVarPath("module.var")

        with patch(
            "pinjected.module_var_path.find_import_statements_in_module"
        ) as mock_find:
            mock_find.return_value = ["import os", "from pathlib import Path"]

            result = mvp.depending_import_lines()

            mock_find.assert_called_once_with("module")
            assert result == ["import os", "from pathlib import Path"]

    def test_to_spec(self):
        """Test to_spec method."""
        mvp = ModuleVarPath("module.var")

        # Patch the load method at the function level
        with patch(
            "pinjected.module_var_path.load_variable_by_module_path"
        ) as mock_load:
            mock_load.return_value = "loaded_value"

            spec = mvp.to_spec()

            assert isinstance(spec, ModuleVarSpec)
            assert spec.var == "loaded_value"
            assert spec.var_path == "module.var"

            mock_load.assert_called_once_with("module.var")

    def test_is_frozen(self):
        """Test that ModuleVarPath is frozen."""
        from dataclasses import fields

        # Check that frozen=True is set
        field_names = {f.name for f in fields(ModuleVarPath)}
        assert "path" in field_names

        # Try to modify and expect error
        mvp = ModuleVarPath("module.var")
        with pytest.raises((AttributeError, TypeError)):
            mvp.path = "new.path"


class TestLoadVariableByModulePath:
    """Test load_variable_by_module_path function."""

    @patch("pinjected.pinjected_logging.logger")
    def test_load_existing_variable(self, mock_logger):
        """Test loading an existing variable."""
        # Use a real module and variable
        result = load_variable_by_module_path("os.path.join")

        # Should load the actual os.path.join function
        import os

        assert result is os.path.join

        # Check logging
        assert mock_logger.info.call_count >= 2

    def test_load_none_path(self):
        """Test loading with None path."""
        # beartype will catch the type error before our ValueError
        with pytest.raises(
            Exception
        ):  # Either TypeError or BeartypeCallHintParamViolation
            load_variable_by_module_path(None)

    def test_load_no_dots(self):
        """Test loading with no dots in path."""
        with pytest.raises(ValueError, match="Empty module name"):
            load_variable_by_module_path("singlename")

    @patch("importlib.import_module")
    def test_import_error(self, mock_import):
        """Test when module import fails."""
        mock_import.side_effect = ImportError("Module not found")

        with pytest.raises(
            ImportError, match="Could not import module 'nonexistent.module'"
        ):
            load_variable_by_module_path("nonexistent.module.var")

    def test_variable_not_found(self):
        """Test when variable doesn't exist in module."""
        # Use a real module and try to access a non-existent attribute
        with pytest.raises(ValueError, match="does not have variable"):
            load_variable_by_module_path("os.non_existent_attribute")

    @patch("importlib.import_module")
    @patch("pinjected.pinjected_logging.logger")
    def test_successful_load_mock_module(self, mock_logger, mock_import):
        """Test successful loading from a mocked module."""
        # Create a mock module with the variable
        mock_module = MagicMock()
        mock_module.test_var = "test_value"
        mock_import.return_value = mock_module

        result = load_variable_by_module_path("test.module.test_var")

        assert result == "test_value"
        assert mock_logger.info.call_count >= 2  # "loading" and "loaded"


class TestFindVarOrFuncDefinitionCodeInModule:
    """Test find_var_or_func_definition_code_in_module function."""

    @patch("importlib.import_module")
    def test_module_import_error(self, mock_import):
        """Test when module cannot be imported."""
        mock_import.side_effect = ImportError("Module not found")

        result = find_var_or_func_definition_code_in_module("nonexistent.module", "var")
        assert result == "Module nonexistent.module could not be imported."

    @patch("importlib.import_module")
    @patch("builtins.open", new_callable=mock_open)
    def test_find_function_definition(self, mock_file, mock_import):
        """Test finding a function definition."""
        # Mock module
        mock_module = MagicMock()
        mock_module.__file__ = "/path/to/module.py"
        mock_import.return_value = mock_module

        # Mock file content
        source_code = """import os

def my_function(a, b):
    '''Docstring'''
    return a + b

class MyClass:
    pass
"""
        mock_file.return_value.readlines.return_value = source_code.splitlines(
            keepends=True
        )

        result = find_var_or_func_definition_code_in_module(
            "test.module", "my_function"
        )

        # Should find the function definition
        assert "def my_function(a, b):" in result
        assert "return a + b" in result

    @patch("importlib.import_module")
    @patch("builtins.open", new_callable=mock_open)
    def test_find_variable_assignment(self, mock_file, mock_import):
        """Test finding a variable assignment."""
        # Mock module
        mock_module = MagicMock()
        mock_module.__file__ = "/path/to/module.py"
        mock_import.return_value = mock_module

        # Mock file content
        source_code = """import os

MY_CONSTANT = 42
my_list = [1, 2, 3]

def func():
    pass
"""
        mock_file.return_value.readlines.return_value = source_code.splitlines(
            keepends=True
        )

        result = find_var_or_func_definition_code_in_module(
            "test.module", "MY_CONSTANT"
        )

        assert "MY_CONSTANT = 42" in result

    @patch("importlib.import_module")
    @patch("builtins.open", new_callable=mock_open)
    def test_find_annotated_assignment(self, mock_file, mock_import):
        """Test finding an annotated assignment."""
        # Mock module
        mock_module = MagicMock()
        mock_module.__file__ = "/path/to/module.py"
        mock_import.return_value = mock_module

        # Mock file content
        source_code = """from typing import List

my_var: int = 10
my_list: List[str] = ["a", "b"]
"""
        mock_file.return_value.readlines.return_value = source_code.splitlines(
            keepends=True
        )

        result = find_var_or_func_definition_code_in_module("test.module", "my_var")

        assert "my_var: int = 10" in result

    @patch("importlib.import_module")
    @patch("builtins.open", new_callable=mock_open)
    def test_async_function_definition(self, mock_file, mock_import):
        """Test finding an async function definition."""
        # Mock module
        mock_module = MagicMock()
        mock_module.__file__ = "/path/to/module.py"
        mock_import.return_value = mock_module

        # Mock file content
        source_code = """import asyncio

async def async_func():
    await asyncio.sleep(1)
    return "done"
"""
        mock_file.return_value.readlines.return_value = source_code.splitlines(
            keepends=True
        )

        result = find_var_or_func_definition_code_in_module("test.module", "async_func")

        assert "async def async_func():" in result
        assert 'return "done"' in result

    @patch("importlib.import_module")
    @patch("builtins.open", new_callable=mock_open)
    def test_definition_not_found(self, mock_file, mock_import):
        """Test when definition is not found."""
        # Mock module
        mock_module = MagicMock()
        mock_module.__file__ = "/path/to/module.py"
        mock_import.return_value = mock_module

        # Mock file content
        source_code = """def other_func():
    pass
"""
        mock_file.return_value.readlines.return_value = source_code.splitlines(
            keepends=True
        )

        with pytest.raises(
            RuntimeError, match="my_var is not defined in the given module"
        ):
            find_var_or_func_definition_code_in_module("test.module", "my_var")

    @pytest.mark.skip(reason="Mock open not working correctly for .pyc file test")
    @patch("importlib.import_module")
    def test_pyc_file_handling(self, mock_import):
        """Test handling of .pyc files."""
        # Mock module with .pyc file
        mock_module = MagicMock()
        mock_module.__file__ = "/path/to/module.pyc"
        mock_import.return_value = mock_module

        # Mock the .py file reading
        source_code = "MY_VAR = 123"

        # The function converts .pyc to .py by removing the 'c'
        # So it will try to open /path/to/module.py
        with patch(
            "pinjected.module_var_path.open",
            mock_open(read_data=source_code),
            create=True,
        ) as mock_file:
            result = find_var_or_func_definition_code_in_module("test.module", "MY_VAR")
            # Verify it tried to open the .py file
            mock_file.assert_called_with("/path/to/module.py")
            assert "MY_VAR = 123" in result


class TestFindImportStatementsInModule:
    """Test find_import_statements_in_module function."""

    @patch("importlib.import_module")
    def test_module_import_error(self, mock_import):
        """Test when module cannot be imported."""
        mock_import.side_effect = ImportError("Module not found")

        result = find_import_statements_in_module("nonexistent.module")
        assert result == "Module nonexistent.module could not be imported."

    @patch("importlib.import_module")
    @patch("builtins.open", new_callable=mock_open)
    def test_find_imports(self, mock_file, mock_import):
        """Test finding import statements."""
        # Mock module
        mock_module = MagicMock()
        mock_module.__file__ = "/path/to/module.py"
        mock_import.return_value = mock_module

        # Mock file content
        source_code = """import os
import sys
from pathlib import Path
from typing import List, Dict
import asyncio as aio

def my_function():
    pass

from collections import defaultdict

class MyClass:
    pass
"""
        mock_file.return_value.readlines.return_value = source_code.splitlines(
            keepends=True
        )

        result = find_import_statements_in_module("test.module")

        assert isinstance(result, list)
        assert "import os" in result
        assert "import sys" in result
        assert "from pathlib import Path" in result
        assert "from typing import List, Dict" in result
        assert "import asyncio as aio" in result
        assert "from collections import defaultdict" in result

    @patch("importlib.import_module")
    @patch("builtins.open", new_callable=mock_open)
    def test_no_imports(self, mock_file, mock_import):
        """Test module with no imports."""
        # Mock module
        mock_module = MagicMock()
        mock_module.__file__ = "/path/to/module.py"
        mock_import.return_value = mock_module

        # Mock file content
        source_code = """# No imports here
MY_VAR = 42

def func():
    return MY_VAR
"""
        mock_file.return_value.readlines.return_value = source_code.splitlines(
            keepends=True
        )

        result = find_import_statements_in_module("test.module")

        assert isinstance(result, list)
        assert len(result) == 0

    @pytest.mark.skip(reason="Mock open not working correctly for .pyc file test")
    @patch("importlib.import_module")
    def test_pyc_file_handling(self, mock_import):
        """Test handling of .pyc files."""
        # Mock module with .pyc file
        mock_module = MagicMock()
        mock_module.__file__ = "/path/to/module.pyc"
        mock_import.return_value = mock_module

        # Mock the .py file reading
        source_code = "import os\nfrom pathlib import Path"

        with patch("builtins.open", mock_open(read_data=source_code)):
            result = find_import_statements_in_module("test.module")
            assert "import os" in result
            assert "from pathlib import Path" in result


class TestLoadVariableFromScript:
    """Test load_variable_from_script function."""

    def test_load_variable_from_script_success(self):
        """Test successfully loading a variable from a script."""
        # Create a temporary script file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("""
MY_VARIABLE = 42
MY_LIST = [1, 2, 3]

def my_function():
    return "hello"
""")
            f.flush()

            script_path = Path(f.name)

            try:
                # Load the variable
                result = load_variable_from_script(script_path, "MY_VARIABLE")
                assert result == 42

                # Load the list
                result_list = load_variable_from_script(script_path, "MY_LIST")
                assert result_list == [1, 2, 3]

                # Load the function
                result_func = load_variable_from_script(script_path, "my_function")
                assert callable(result_func)
                assert result_func() == "hello"
            finally:
                script_path.unlink()

    def test_load_variable_not_found(self):
        """Test loading non-existent variable."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("EXISTING_VAR = 123")
            f.flush()

            script_path = Path(f.name)

            try:
                with pytest.raises(AttributeError):
                    load_variable_from_script(script_path, "NON_EXISTENT_VAR")
            finally:
                script_path.unlink()

    def test_load_from_script_with_imports(self):
        """Test loading from script with imports."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("""
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent
OS_NAME = os.name
""")
            f.flush()

            script_path = Path(f.name)

            try:
                # Load the Path variable
                result = load_variable_from_script(script_path, "BASE_DIR")
                assert isinstance(result, Path)

                # Load the os.name variable
                result_os = load_variable_from_script(script_path, "OS_NAME")
                assert isinstance(result_os, str)
            finally:
                script_path.unlink()

    def test_load_from_script_with_syntax_error(self):
        """Test loading from script with syntax error."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("invalid python syntax {{{")
            f.flush()

            script_path = Path(f.name)

            try:
                with pytest.raises(SyntaxError):
                    load_variable_from_script(script_path, "anything")
            finally:
                script_path.unlink()

    @patch("importlib.util.spec_from_file_location")
    def test_load_with_spec_error(self, mock_spec):
        """Test when spec creation fails."""
        mock_spec.return_value = None

        with pytest.raises(AttributeError):
            load_variable_from_script(Path("/fake/path.py"), "var")


class TestModuleVarPathAdditional:
    """Additional tests for ModuleVarPath to improve coverage."""

    def test_module_file_path_not_in_sys_modules(self):
        """Test module_file_path when module needs to be imported."""
        # Create a unique module name that's not imported
        unique_module = "test_module_that_does_not_exist_12345"

        # Mock __import__ and sys.modules to simulate import
        with (
            patch("sys.modules", {}) as mock_modules,
            patch("builtins.__import__") as mock_import,
        ):
            # Set up the mock module
            mock_module = Mock()
            mock_module.__file__ = "/path/to/module.py"

            # When imported, add to sys.modules
            def import_side_effect(name):
                if name == unique_module:
                    mock_modules[name] = mock_module
                return mock_module

            mock_import.side_effect = import_side_effect

            # Create ModuleVarPath and test
            mvp = ModuleVarPath(f"{unique_module}.test_var")
            result = mvp.module_file_path

            assert result == Path("/path/to/module.py")
            mock_import.assert_called_once_with(unique_module)


class TestPycFileHandling:
    """Tests for .pyc file handling to improve coverage."""

    def test_find_var_or_func_definition_pyc_file(self, tmp_path):
        """Test finding definition when module file is .pyc."""
        # Create a .py file with content
        py_file = tmp_path / "test_module.py"
        py_file.write_text("def test_func():\n    pass")

        # Mock the module with .pyc file
        mock_module = Mock()
        mock_module.__file__ = str(tmp_path / "test_module.pyc")

        with patch("sys.modules", {"test_module": mock_module}):
            code_lines = find_var_or_func_definition_code_in_module(
                "test_module", "test_func"
            )
            assert code_lines is not None
            assert "def test_func():" in code_lines

    def test_find_import_statements_pyc_file(self, tmp_path):
        """Test finding imports when module file is .pyc."""
        # Create a .py file with imports
        py_file = tmp_path / "test_module.py"
        py_file.write_text(
            "import os\nfrom pathlib import Path\n\ndef test_func():\n    pass"
        )

        # Mock the module with .pyc file
        mock_module = Mock()
        mock_module.__file__ = str(tmp_path / "test_module.pyc")

        with patch("sys.modules", {"test_module": mock_module}):
            imports = find_import_statements_in_module("test_module")
            assert len(imports) == 2
            assert "import os" in imports[0]
            assert "from pathlib import Path" in imports[1]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
