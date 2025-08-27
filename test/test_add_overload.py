"""Comprehensive tests for pinjected/di/tools/add_overload.py module."""

import pytest
import ast
import inspect
import tempfile
import os
from unittest.mock import patch

from pinjected.di.tools.add_overload import (
    process_file,
    add_overload_import,
    has_injected_decorator,
    get_function_signature,
    update_function_signature,
    generate_overload_signature,
    get_annotation_string,
    inject_overload_signature,
    remove_overload_signature,
    has_overload_decorator,
    add_overload,
)


class TestProcessFile:
    """Tests for process_file function."""

    def test_process_file_with_injected_function(self):
        """Test processing file with @injected function."""
        source_code = """
from pinjected import injected

@injected
def my_func(dep1, /, arg1: str, arg2: int = 5) -> str:
    return f"{dep1}: {arg1} {arg2}"
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(source_code)
            f.flush()

            try:
                process_file(f.name)

                # Read the processed file
                with open(f.name) as rf:
                    result = rf.read()

                # Should add overload import
                assert "from typing import overload" in result
                # Should add overload signature
                assert "@overload" in result
                assert "def my_func(arg1: str, arg2: int) -> str:" in result
            finally:
                os.unlink(f.name)

    def test_process_file_without_injected(self):
        """Test processing file without @injected functions."""
        source_code = """
def regular_func(x, y):
    return x + y
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(source_code)
            f.flush()

            try:
                process_file(f.name)

                with open(f.name) as rf:
                    result = rf.read()

                # Should not add overload import
                assert "from typing import overload" not in result
                assert "@overload" not in result
            finally:
                os.unlink(f.name)

    def test_process_file_removes_existing_overload(self):
        """Test that processing removes existing overload for non-injected functions."""
        source_code = """
from typing import overload

@overload
def regular_func(x: int) -> int:
    ...

def regular_func(x):
    return x
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(source_code)
            f.flush()

            try:
                process_file(f.name)

                with open(f.name) as rf:
                    result = rf.read()

                # Should remove the overload
                assert result.count("@overload") == 0
                assert result.count("def regular_func") == 1
            finally:
                os.unlink(f.name)


class TestAddOverloadImport:
    """Tests for add_overload_import function."""

    def test_add_overload_import_new(self):
        """Test adding overload import when not present."""
        tree = ast.parse("")

        add_overload_import(tree)

        # Should add import at the beginning
        assert len(tree.body) == 1
        import_node = tree.body[0]
        assert isinstance(import_node, ast.ImportFrom)
        assert import_node.module == "typing"
        assert any(alias.name == "overload" for alias in import_node.names)

    def test_add_overload_import_existing(self):
        """Test not adding overload import when already present."""
        source = "from typing import overload\n"
        tree = ast.parse(source)

        original_length = len(tree.body)
        add_overload_import(tree)

        # Should not add duplicate
        assert len(tree.body) == original_length

    def test_add_overload_import_with_other_typing_imports(self):
        """Test adding overload when other typing imports exist."""
        source = "from typing import List, Dict\n"
        tree = ast.parse(source)

        add_overload_import(tree)

        # Should add new import node
        assert len(tree.body) == 2


class TestHasInjectedDecorator:
    """Tests for has_injected_decorator function."""

    def test_has_injected_decorator_true(self):
        """Test detecting @injected decorator."""
        source = """
@injected
def func():
    pass
"""
        tree = ast.parse(source)
        func_node = tree.body[0]

        assert has_injected_decorator(func_node) is True

    def test_has_injected_decorator_false(self):
        """Test not detecting @injected when absent."""
        source = """
@other_decorator
def func():
    pass
"""
        tree = ast.parse(source)
        func_node = tree.body[0]

        assert has_injected_decorator(func_node) is False

    def test_has_injected_decorator_no_decorators(self):
        """Test with function having no decorators."""
        source = """
def func():
    pass
"""
        tree = ast.parse(source)
        func_node = tree.body[0]

        assert has_injected_decorator(func_node) is False


class TestGetFunctionSignature:
    """Tests for get_function_signature function."""

    def test_get_function_signature_simple(self):
        """Test getting signature of simple function."""
        source = """
def func(a, b):
    pass
"""
        tree = ast.parse(source)
        func_node = tree.body[0]

        sig = get_function_signature(func_node)

        assert len(sig.parameters) == 2
        assert "a" in sig.parameters
        assert "b" in sig.parameters

    def test_get_function_signature_with_defaults(self):
        """Test getting signature with default values."""
        source = """
def func(a, b=5, c="test"):
    pass
"""
        tree = ast.parse(source)
        func_node = tree.body[0]

        sig = get_function_signature(func_node)

        assert sig.parameters["a"].default == inspect.Parameter.empty
        assert sig.parameters["b"].default == 5
        assert sig.parameters["c"].default == "test"

    def test_get_function_signature_with_annotations(self):
        """Test getting signature with type annotations."""
        source = """
def func(a: int, b: str) -> bool:
    pass
"""
        tree = ast.parse(source)
        func_node = tree.body[0]

        sig = get_function_signature(func_node)

        assert sig.parameters["a"].annotation == "int"
        assert sig.parameters["b"].annotation == "str"
        assert sig.return_annotation == "bool"

    def test_get_function_signature_positional_only(self):
        """Test getting signature with positional-only parameters."""
        source = """
def func(a, b, /, c, d):
    pass
"""
        tree = ast.parse(source)
        func_node = tree.body[0]

        sig = get_function_signature(func_node)

        # First two should be positional-only
        params_list = list(sig.parameters.values())
        assert params_list[0].kind == inspect.Parameter.POSITIONAL_ONLY
        assert params_list[1].kind == inspect.Parameter.POSITIONAL_ONLY
        assert params_list[2].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD
        assert params_list[3].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


class TestUpdateFunctionSignature:
    """Tests for update_function_signature function."""

    def test_update_function_signature_removes_positional_only(self):
        """Test that positional-only parameters are removed."""
        # Create a signature with positional-only params
        params = [
            inspect.Parameter("a", inspect.Parameter.POSITIONAL_ONLY),
            inspect.Parameter("b", inspect.Parameter.POSITIONAL_ONLY),
            inspect.Parameter("c", inspect.Parameter.POSITIONAL_OR_KEYWORD),
        ]
        original_sig = inspect.Signature(params)

        updated_sig = update_function_signature(original_sig)

        # Should only have one parameter (c)
        assert len(updated_sig.parameters) == 1
        assert "c" in updated_sig.parameters
        assert "a" not in updated_sig.parameters
        assert "b" not in updated_sig.parameters

    def test_update_function_signature_preserves_others(self):
        """Test that non-positional-only parameters are preserved."""
        params = [
            inspect.Parameter("a", inspect.Parameter.POSITIONAL_OR_KEYWORD),
            inspect.Parameter("b", inspect.Parameter.KEYWORD_ONLY, default=5),
        ]
        original_sig = inspect.Signature(params)

        updated_sig = update_function_signature(original_sig)

        assert len(updated_sig.parameters) == 2
        assert updated_sig.parameters["b"].default == 5


class TestGenerateOverloadSignature:
    """Tests for generate_overload_signature function."""

    def test_generate_overload_signature_simple(self):
        """Test generating simple overload signature."""
        params = [
            inspect.Parameter("x", inspect.Parameter.POSITIONAL_OR_KEYWORD),
            inspect.Parameter("y", inspect.Parameter.POSITIONAL_OR_KEYWORD),
        ]
        sig = inspect.Signature(params)

        result = generate_overload_signature("my_func", sig)

        assert "@overload" in result
        assert "def my_func(x, y):" in result
        assert '"""Signature of the function after being injected."""' in result
        assert "..." in result

    def test_generate_overload_signature_with_annotations(self):
        """Test generating overload with type annotations."""
        params = [
            inspect.Parameter(
                "x", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=int
            ),
            inspect.Parameter(
                "y", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=str
            ),
        ]
        sig = inspect.Signature(params, return_annotation=bool)

        result = generate_overload_signature("my_func", sig)

        assert "def my_func(x: int, y: str) -> bool:" in result

    def test_generate_overload_signature_with_string_annotations(self):
        """Test generating overload with string annotations."""
        params = [
            inspect.Parameter(
                "x", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation="List[int]"
            ),
        ]
        sig = inspect.Signature(params, return_annotation="Optional[str]")

        result = generate_overload_signature("typed_func", sig)

        assert "def typed_func(x: List[int]) -> Optional[str]:" in result


class TestGetAnnotationString:
    """Tests for get_annotation_string function."""

    def test_get_annotation_string_with_str(self):
        """Test with string annotation."""
        assert get_annotation_string("List[int]") == "List[int]"

    def test_get_annotation_string_with_type(self):
        """Test with type annotation."""
        assert get_annotation_string(int) == "int"
        assert get_annotation_string(str) == "str"

    def test_get_annotation_string_with_class(self):
        """Test with custom class annotation."""

        class MyClass:
            pass

        assert get_annotation_string(MyClass) == "MyClass"

    def test_get_annotation_string_fallback(self):
        """Test fallback to str() for unknown types."""
        obj = object()
        result = get_annotation_string(obj)
        assert isinstance(result, str)


class TestInjectOverloadSignature:
    """Tests for inject_overload_signature function."""

    def test_inject_overload_signature(self):
        """Test injecting overload signature into AST."""
        source = """
def my_func(x):
    return x
"""
        tree = ast.parse(source)
        func_node = tree.body[0]

        overload_sig = """
@overload
def my_func(x: int) -> int:
    ...
"""

        inject_overload_signature(tree, func_node, overload_sig)

        # Should have two nodes now
        assert len(tree.body) == 2
        # First should be overload
        assert isinstance(tree.body[0], ast.FunctionDef)
        assert tree.body[0].name == "my_func"
        # Original function should be second
        assert tree.body[1] == func_node


class TestRemoveOverloadSignature:
    """Tests for remove_overload_signature function."""

    def test_remove_overload_signature_exists(self):
        """Test removing existing overload signature."""
        source = """
@overload
def my_func(x: int) -> int:
    ...

def my_func(x):
    return x
"""
        tree = ast.parse(source)
        func_node = tree.body[1]  # The actual function

        remove_overload_signature(tree, func_node)

        # Should only have one function left
        assert len(tree.body) == 1
        assert tree.body[0] == func_node

    def test_remove_overload_signature_not_exists(self):
        """Test removing when no overload exists."""
        source = """
def other_func():
    pass

def my_func(x):
    return x
"""
        tree = ast.parse(source)
        func_node = tree.body[1]

        original_length = len(tree.body)
        remove_overload_signature(tree, func_node)

        # Should not change anything
        assert len(tree.body) == original_length


class TestHasOverloadDecorator:
    """Tests for has_overload_decorator function."""

    def test_has_overload_decorator_true(self):
        """Test detecting @overload decorator."""
        source = """
@overload
def func():
    pass
"""
        tree = ast.parse(source)
        func_node = tree.body[0]

        assert has_overload_decorator(func_node) is True

    def test_has_overload_decorator_false(self):
        """Test not detecting @overload when absent."""
        source = """
@other_decorator
def func():
    pass
"""
        tree = ast.parse(source)
        func_node = tree.body[0]

        assert has_overload_decorator(func_node) is False


class TestAddOverload:
    """Tests for add_overload function."""

    @patch("pinjected.di.tools.add_overload.process_file")
    def test_add_overload_function(self, mock_process):
        """Test the main add_overload function."""
        # add_overload is an @injected function, so we need to access the wrapped function
        if hasattr(add_overload, "__wrapped__"):
            func = add_overload.__wrapped__
        elif hasattr(add_overload, "src_function"):
            func = add_overload.src_function
        else:
            # For newer versions, we may need to get the original function differently
            func = add_overload.target_function

        result = func("/path/to/file.py")

        mock_process.assert_called_once_with("/path/to/file.py")
        assert result == 0


class TestIntegration:
    """Integration tests for add_overload module."""

    def test_full_processing_workflow(self):
        """Test complete workflow of processing a file."""
        source_code = """
from pinjected import injected

class MyClass:
    @injected
    def method(self, dep, /, x: int, y: str = "default") -> str:
        return f"{dep}: {x} {y}"

@injected
def standalone(service, /, data: dict) -> None:
    print(service, data)

def regular_function(a, b):
    return a + b
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(source_code)
            f.flush()

            try:
                process_file(f.name)

                with open(f.name) as rf:
                    result = rf.read()

                # Check results
                assert "from typing import overload" in result
                # Should have overload for method
                assert "@overload" in result
                assert "def method(self, x: int, y: str) -> str:" in result
                # Should have overload for standalone
                assert "def standalone(data: dict) -> None:" in result
                # Should not modify regular_function
                assert result.count("def regular_function") == 1
            finally:
                os.unlink(f.name)

    def test_module_level_variables(self):
        """Test that module-level variables are defined."""
        from pinjected.di.tools.add_overload import design_obj, __design__

        assert design_obj is not None
        assert __design__ is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
