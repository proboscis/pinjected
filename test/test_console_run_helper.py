"""Comprehensive tests for pinjected/ide_supports/console_run_helper.py module."""

import pytest
import ast
import json
import os
from unittest.mock import patch
import tempfile
from click.testing import CliRunner

from pinjected.ide_supports.console_run_helper import (
    main,
    extract_func_source_and_imports,
    extract_func_source_and_imports_dict,
    WithBlockVisitor,
    extract_with_block_structure,
    extrract_assignments,
    generate_code_with_reload,
    reload,
    is_pydevd,
)


class TestMainCommand:
    """Tests for the main Click command group."""

    def test_main_command(self):
        """Test main command runs without error."""
        runner = CliRunner()
        result = runner.invoke(main, [])
        assert result.exit_code == 0

    def test_main_command_help(self):
        """Test main command help."""
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "Usage:" in result.output


class TestExtractFuncSourceAndImports:
    """Tests for extract_func_source_and_imports command."""

    def test_extract_func_source_and_imports_basic(self):
        """Test extracting function source and imports."""
        runner = CliRunner()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("""
import os
from pathlib import Path

def test_function(x, y):
    return x + y

def another_function():
    pass
""")
            f.flush()

            try:
                result = runner.invoke(
                    extract_func_source_and_imports, [f.name, "test_function"]
                )

                assert result.exit_code == 0
                assert "<pinjected>" in result.output
                assert "</pinjected>" in result.output

                # Extract JSON from output
                json_start = result.output.find("<pinjected>") + 11
                json_end = result.output.find("</pinjected>")
                json_str = result.output[json_start:json_end].strip()
                data = json.loads(json_str)

                assert "code" in data
                assert "imports" in data
                assert "def test_function(x, y):" in data["code"]
                assert "import os" in data["imports"]
                assert "from pathlib import Path" in data["imports"]
            finally:
                os.unlink(f.name)

    def test_extract_func_source_and_imports_not_found(self):
        """Test extracting non-existent function."""
        runner = CliRunner()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("def test_function():\n    pass")
            f.flush()

            try:
                result = runner.invoke(
                    extract_func_source_and_imports, [f.name, "non_existent_function"]
                )

                assert result.exit_code == 0
                json_start = result.output.find("<pinjected>") + 11
                json_end = result.output.find("</pinjected>")
                json_str = result.output[json_start:json_end].strip()
                data = json.loads(json_str)

                assert "Function non_existent_function not found." in data["code"]
            finally:
                os.unlink(f.name)

    def test_extract_func_source_and_imports_with_decorators(self):
        """Test extracting function with decorators."""
        runner = CliRunner()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("""
from functools import wraps

@wraps(print)
@staticmethod
def decorated_func():
    return "decorated"
""")
            f.flush()

            try:
                result = runner.invoke(
                    extract_func_source_and_imports, [f.name, "decorated_func"]
                )

                assert result.exit_code == 0
                json_start = result.output.find("<pinjected>") + 11
                json_end = result.output.find("</pinjected>")
                json_str = result.output[json_start:json_end].strip()
                data = json.loads(json_str)

                assert "@wraps" in data["code"]
                assert "@staticmethod" in data["code"]
                assert "def decorated_func():" in data["code"]
            finally:
                os.unlink(f.name)


class TestExtractFuncSourceAndImportsDict:
    """Tests for extract_func_source_and_imports_dict function."""

    def test_extract_func_source_and_imports_dict_basic(self):
        """Test extracting functions and imports as dict."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("""
import sys
from os import path
import json as j

def func1():
    pass

def func2(a, b):
    return a + b

class MyClass:
    def method(self):
        pass
""")
            f.flush()

            try:
                result = extract_func_source_and_imports_dict(f.name)

                assert "functions" in result
                assert "imports" in result
                assert "func1" in result["functions"]
                assert "func2" in result["functions"]
                assert "import sys" in result["imports"]
                assert "from os import path" in result["imports"]
                assert "import json as j" in result["imports"]
            finally:
                os.unlink(f.name)

    def test_extract_func_source_and_imports_dict_empty_file(self):
        """Test extracting from empty file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("")
            f.flush()

            try:
                result = extract_func_source_and_imports_dict(f.name)
                assert result["functions"] == {}
                assert result["imports"] == []
            finally:
                os.unlink(f.name)


class TestWithBlockVisitor:
    """Tests for WithBlockVisitor class."""

    def test_with_block_visitor_reload(self):
        """Test WithBlockVisitor with reload context."""
        source = """
with reload("func1", "func2"):
    x: int = 1
    y: str = "test"
"""
        parsed = ast.parse(source)
        visitor = WithBlockVisitor()
        visitor.visit(parsed)

        assert "x" in visitor.result
        assert "y" in visitor.result
        assert visitor.result["x"]["reload_targets"] == ["func1", "func2"]
        assert visitor.result["y"]["reload_targets"] == ["func1", "func2"]

    def test_with_block_visitor_no_reload(self):
        """Test WithBlockVisitor without reload context."""
        source = """
with open("file.txt") as f:
    content = f.read()
"""
        parsed = ast.parse(source)
        visitor = WithBlockVisitor()
        visitor.visit(parsed)

        assert visitor.result == {}

    def test_with_block_visitor_nested(self):
        """Test WithBlockVisitor with nested context."""
        source = """
with reload("func1"):
    with open("file.txt"):
        x: int = 1
    y: str = "test"
"""
        parsed = ast.parse(source)
        visitor = WithBlockVisitor()
        visitor.visit(parsed)

        assert "y" in visitor.result
        assert visitor.result["y"]["reload_targets"] == ["func1"]


class TestExtractWithBlockStructure:
    """Tests for extract_with_block_structure function."""

    def test_extract_with_block_structure_basic(self):
        """Test extracting with block structure."""
        source = """
with reload("test_func"):
    var1: int = 42
    var2: str = "hello"
"""
        result = extract_with_block_structure(source)

        assert "var1" in result
        assert "var2" in result
        assert result["var1"]["reload_targets"] == ["test_func"]
        assert result["var2"]["reload_targets"] == ["test_func"]

    def test_extract_with_block_structure_multiple_targets(self):
        """Test with multiple reload targets."""
        source = """
with reload("func1", "func2", "func3"):
    injected_var: Any = some_injected
"""
        result = extract_with_block_structure(source)

        assert "injected_var" in result
        assert result["injected_var"]["reload_targets"] == ["func1", "func2", "func3"]

    def test_extract_with_block_structure_empty(self):
        """Test with no reload blocks."""
        source = "x = 1\ny = 2"
        result = extract_with_block_structure(source)
        assert result == {}


class TestExtractAssignments:
    """Tests for extrract_assignments function."""

    def test_extract_assignments_basic(self):
        """Test extracting basic assignments."""
        source = """
x = 42
y = "hello"
z = [1, 2, 3]
"""
        result = extrract_assignments(source)

        assert "x" in result
        assert "y" in result
        assert "z" in result
        assert result["x"] == "42"
        assert result["y"] == '"hello"'
        assert result["z"] == "[1, 2, 3]"

    def test_extract_assignments_with_annotations(self):
        """Test extracting annotated assignments."""
        source = """
x: int = 42
y: str = "hello"
z: list[int] = [1, 2, 3]
"""
        result = extrract_assignments(source)

        assert "x" in result
        assert "y" in result
        assert "z" in result
        assert result["x"] == "42"
        assert result["y"] == '"hello"'
        assert result["z"] == "[1, 2, 3]"

    def test_extract_assignments_tuple(self):
        """Test extracting tuple assignments."""
        source = """
a, b = 1, 2
x, y, z = [1, 2, 3]
"""
        result = extrract_assignments(source)

        assert "a" in result
        assert "b" in result
        assert "x" in result
        assert "y" in result
        assert "z" in result
        # All variables from tuple assignment get the full RHS
        assert result["a"] == "1, 2"
        assert result["b"] == "1, 2"

    def test_extract_assignments_complex(self):
        """Test extracting complex assignments."""
        source = """
func_result = some_function(1, 2, 3)
dict_access = my_dict["key"]
attr_access = obj.attribute
"""
        result = extrract_assignments(source)

        assert "func_result" in result
        assert "dict_access" in result
        assert "attr_access" in result
        assert result["func_result"] == "some_function(1, 2, 3)"
        assert result["dict_access"] == 'my_dict["key"]'
        assert result["attr_access"] == "obj.attribute"


class TestGenerateCodeWithReload:
    """Tests for generate_code_with_reload command."""

    @patch(
        "pinjected.ide_supports.console_run_helper.extract_func_source_and_imports_dict"
    )
    @patch("pinjected.ide_supports.console_run_helper.extract_with_block_structure")
    @patch("pinjected.ide_supports.console_run_helper.extrract_assignments")
    def test_generate_code_with_reload_basic(
        self, mock_assignments, mock_reload, mock_funcs
    ):
        """Test generating code with reload."""
        runner = CliRunner()

        # Setup mocks
        mock_funcs.return_value = {
            "functions": {
                "func1": "def func1():\n    return 1",
                "func2": "def func2():\n    return 2",
            },
            "imports": ["import os", "from pathlib import Path"],
        }

        mock_reload.return_value = {"test_var": {"reload_targets": ["func1", "func2"]}}

        mock_assignments.return_value = {"test_var": "some_injected_function()"}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("# test file")
            f.flush()

            try:
                result = runner.invoke(generate_code_with_reload, [f.name, "test_var"])

                assert result.exit_code == 0
                assert "<pinjected>" in result.output
                assert "</pinjected>" in result.output

                # Extract JSON from output
                json_start = result.output.find("<pinjected>") + 11
                json_end = result.output.find("</pinjected>")
                json_str = result.output[json_start:json_end].strip()
                data = json.loads(json_str)

                assert "code" in data
                assert "def func1():" in data["code"]
                assert "def func2():" in data["code"]
                assert "import os" in data["code"]
                assert "test_var = some_injected_function()" in data["code"]
            finally:
                os.unlink(f.name)

    @patch(
        "pinjected.ide_supports.console_run_helper.extract_func_source_and_imports_dict"
    )
    @patch("pinjected.ide_supports.console_run_helper.extract_with_block_structure")
    @patch("pinjected.ide_supports.console_run_helper.extrract_assignments")
    def test_generate_code_with_reload_no_reload_targets(
        self, mock_assignments, mock_reload, mock_funcs
    ):
        """Test generating code without reload targets."""
        runner = CliRunner()

        mock_funcs.return_value = {
            "functions": {"func1": "def func1():\n    pass"},
            "imports": [],
        }

        mock_reload.return_value = {}  # No reload targets

        mock_assignments.return_value = {"test_var": "simple_value"}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("# test file")
            f.flush()

            try:
                result = runner.invoke(generate_code_with_reload, [f.name, "test_var"])

                assert result.exit_code == 0
                json_start = result.output.find("<pinjected>") + 11
                json_end = result.output.find("</pinjected>")
                json_str = result.output[json_start:json_end].strip()
                data = json.loads(json_str)

                # Should not include func1 since it's not in reload targets
                assert "def func1():" not in data["code"]
                assert "test_var = simple_value" in data["code"]
            finally:
                os.unlink(f.name)


class TestTestTargetFunction:
    """Tests for test_target_function."""

    def test_test_target_function(self, capsys):
        """Test test_target_function prints hello."""
        # test_target_function is an @injected function, so we need to access
        # the underlying function through the dependency injection system

        # Since test_target_function has no dependencies (no positional-only params),
        # we can call it through a simple design
        from pinjected import design
        from pinjected.ide_supports.console_run_helper import test_target_function

        # Create a simple design and resolver
        d = design()
        resolver = d.to_resolver()

        # Execute the function through the resolver
        # The resolver provides a Partial object, which we need to call
        import asyncio

        func = asyncio.run(resolver.provide(test_target_function))

        # Call the resolved function
        func()

        captured = capsys.readouterr()
        assert "hello" in captured.out


class TestReloadContextManager:
    """Tests for reload context manager."""

    def test_reload_context_manager(self):
        """Test reload context manager."""
        # It's just a placeholder, so test it doesn't raise
        with reload("func1", "func2"):
            x = 1
        assert x == 1


class TestIsPydevd:
    """Tests for is_pydevd function."""

    def test_is_pydevd_true(self):
        """Test when PYDEVD_LOAD_VALUES_ASYNC is set."""
        with patch.dict(os.environ, {"PYDEVD_LOAD_VALUES_ASYNC": "1"}):
            assert is_pydevd() is True

    def test_is_pydevd_false(self):
        """Test when PYDEVD_LOAD_VALUES_ASYNC is not set."""
        with patch.dict(os.environ, {}, clear=True):
            assert is_pydevd() is False

    def test_is_pydevd_empty_value(self):
        """Test when PYDEVD_LOAD_VALUES_ASYNC is empty."""
        with patch.dict(os.environ, {"PYDEVD_LOAD_VALUES_ASYNC": ""}):
            assert is_pydevd() is True  # Still True because key exists


class TestIntegration:
    """Integration tests for console_run_helper."""

    def test_full_workflow(self):
        """Test complete workflow of extracting and reloading."""
        source_code = """
import os
from pathlib import Path

@injected
def my_injected_func():
    return "injected result"

def helper_func():
    return "helper"

with reload("my_injected_func", "helper_func"):
    my_var: Any = my_injected_func()
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(source_code)
            f.flush()

            try:
                # Extract functions
                func_dict = extract_func_source_and_imports_dict(f.name)
                assert "my_injected_func" in func_dict["functions"]
                assert "helper_func" in func_dict["functions"]

                # Extract reload structure
                reload_structure = extract_with_block_structure(source_code)
                assert "my_var" in reload_structure
                assert reload_structure["my_var"]["reload_targets"] == [
                    "my_injected_func",
                    "helper_func",
                ]

                # Extract assignments
                assignments = extrract_assignments(source_code)
                assert "my_var" in assignments
                assert assignments["my_var"] == "my_injected_func()"
            finally:
                os.unlink(f.name)

    def test_cli_commands_available(self):
        """Test that all CLI commands are available."""
        runner = CliRunner()

        # Test main help
        result = runner.invoke(main, ["--help"])
        assert "extract-func-source-and-imports" in result.output
        assert "generate-code-with-reload" in result.output

        # Test subcommand help
        result = runner.invoke(main, ["extract-func-source-and-imports", "--help"])
        assert result.exit_code == 0
        assert "SCRIPT_PATH" in result.output
        assert "FUNC_NAME" in result.output

        result = runner.invoke(main, ["generate-code-with-reload", "--help"])
        assert result.exit_code == 0
        assert "SCRIPT_PATH" in result.output
        assert "TARGET_NAME" in result.output


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
