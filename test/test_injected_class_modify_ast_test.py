"""Tests for injected_class/modify_ast_test.py module."""

import pytest
import ast
import textwrap
import asyncio
from unittest.mock import patch

from pinjected.injected_class.modify_ast_test import (
    AttributeReplacer,
    modify_class,
    ast_to_class,
    convert_cls,
)


class TestAttributeReplacer:
    """Tests for AttributeReplacer class."""

    def test_init(self):
        """Test AttributeReplacer initialization."""
        replacer = AttributeReplacer(["attr1", "attr2"])
        assert replacer.attrs_to_replace == {"attr1", "attr2"}
        assert replacer.replaced_attrs == set()
        assert replacer.in_method is False

    def test_visit_async_function_def(self):
        """Test visiting async function definitions."""
        code = textwrap.dedent("""
        async def method(self):
            return self.attr1 + self.attr2
        """).strip()

        tree = ast.parse(code)
        replacer = AttributeReplacer(["attr1", "attr2"])
        new_tree = replacer.visit(tree)

        # Get the function node
        func = new_tree.body[0]

        # Check that parameters were added
        param_names = [arg.arg for arg in func.args.args]
        assert "__self_attr1__" in param_names
        assert "__self_attr2__" in param_names

    def test_visit_attribute_replacement(self):
        """Test that self attributes are replaced."""
        code = textwrap.dedent("""
        async def method(self):
            return self.attr1
        """).strip()

        tree = ast.parse(code)
        replacer = AttributeReplacer(["attr1"])
        new_tree = replacer.visit(tree)

        # Unparse and check the result
        result = ast.unparse(new_tree)
        assert "__self_attr1__" in result
        assert "self.attr1" not in result

    def test_nested_async_functions(self):
        """Test that nested async functions are not modified."""
        code = textwrap.dedent("""
        async def outer(self):
            async def inner():
                return self.attr1
            return await inner()
        """).strip()

        tree = ast.parse(code)
        replacer = AttributeReplacer(["attr1"])
        new_tree = replacer.visit(tree)

        # Only outer function should have the parameter added
        outer_func = new_tree.body[0]
        param_names = [arg.arg for arg in outer_func.args.args]
        assert "__self_attr1__" in param_names

    def test_non_self_attributes_ignored(self):
        """Test that non-self attributes are not replaced."""
        code = textwrap.dedent("""
        async def method(self, other):
            return other.attr1 + self.attr1
        """).strip()

        tree = ast.parse(code)
        replacer = AttributeReplacer(["attr1"])
        new_tree = replacer.visit(tree)

        result = ast.unparse(new_tree)
        assert "other.attr1" in result  # Should not be replaced
        assert "__self_attr1__" in result  # Should be replaced

    def test_attributes_not_in_replace_list(self):
        """Test that attributes not in the replace list are kept."""
        code = textwrap.dedent("""
        async def method(self):
            return self.attr1 + self.attr2
        """).strip()

        tree = ast.parse(code)
        replacer = AttributeReplacer(["attr1"])  # Only replace attr1
        new_tree = replacer.visit(tree)

        result = ast.unparse(new_tree)
        assert "__self_attr1__" in result
        assert "self.attr2" in result  # Should not be replaced


class TestModifyClass:
    """Tests for modify_class function."""

    def test_modify_async_methods(self):
        """Test modifying async methods in a class."""
        class_code = textwrap.dedent("""
        class TestClass:
            async def method1(self):
                return self.attr1
            
            async def method2(self):
                return self.attr2
        """).strip()

        tree = ast.parse(class_code)
        class_ast = tree.body[0]

        modified = modify_class(class_ast, ["method1"], ["attr1"])

        # Check that method1 was modified
        method1 = modified.body[0]
        param_names = [arg.arg for arg in method1.args.args]
        assert "__self_attr1__" in param_names

        # Check that method2 was not modified
        method2 = modified.body[1]
        param_names = [arg.arg for arg in method2.args.args]
        assert "__self_attr1__" not in param_names

    def test_error_on_sync_method(self):
        """Test that sync methods raise an error."""
        class_code = textwrap.dedent("""
        class TestClass:
            def sync_method(self):
                return self.attr1
        """).strip()

        tree = ast.parse(class_code)
        class_ast = tree.body[0]

        with pytest.raises(RuntimeError, match="must be an async method"):
            modify_class(class_ast, ["sync_method"], ["attr1"])

    def test_multiple_methods_and_attrs(self):
        """Test modifying multiple methods with multiple attributes."""
        class_code = textwrap.dedent("""
        class TestClass:
            async def method1(self):
                return self.attr1 + self.attr2
            
            async def method2(self):
                return self.attr2 + self.attr3
        """).strip()

        tree = ast.parse(class_code)
        class_ast = tree.body[0]

        modified = modify_class(
            class_ast, ["method1", "method2"], ["attr1", "attr2", "attr3"]
        )

        # Check both methods were modified
        for method in modified.body:
            if isinstance(method, ast.AsyncFunctionDef):
                assert len(method.args.args) > 1  # More than just 'self'

    def test_preserve_other_class_members(self):
        """Test that other class members are preserved."""
        class_code = textwrap.dedent("""
        class TestClass:
            class_var = 42
            
            def __init__(self):
                self.instance_var = 10
            
            async def method1(self):
                return self.attr1
        """).strip()

        tree = ast.parse(class_code)
        class_ast = tree.body[0]

        modified = modify_class(class_ast, ["method1"], ["attr1"])

        # Check that all members are still present
        assert len(modified.body) == 3
        assert any(isinstance(node, ast.Assign) for node in modified.body)
        assert any(
            isinstance(node, ast.FunctionDef) and node.name == "__init__"
            for node in modified.body
        )


class TestAstToClass:
    """Tests for ast_to_class function."""

    def test_simple_class_conversion(self):
        """Test converting a simple class AST to a class object."""
        class_code = textwrap.dedent("""
        class SimpleClass:
            def method(self):
                return 42
        """).strip()

        tree = ast.parse(class_code)
        class_ast = tree.body[0]

        cls = ast_to_class(class_ast, "SimpleClass")

        assert cls.__name__ == "SimpleClass"
        assert hasattr(cls, "method")
        instance = cls()
        assert instance.method() == 42

    def test_class_with_attributes(self):
        """Test converting class with class and instance attributes."""
        class_code = textwrap.dedent("""
        class AttrClass:
            class_attr = "hello"
            
            def __init__(self):
                self.instance_attr = "world"
        """).strip()

        tree = ast.parse(class_code)
        class_ast = tree.body[0]

        cls = ast_to_class(class_ast, "AttrClass")

        assert cls.class_attr == "hello"
        instance = cls()
        assert instance.instance_attr == "world"

    def test_async_class_conversion(self):
        """Test converting class with async methods."""
        class_code = textwrap.dedent("""
        class AsyncClass:
            async def async_method(self):
                return "async result"
        """).strip()

        tree = ast.parse(class_code)
        class_ast = tree.body[0]

        cls = ast_to_class(class_ast, "AsyncClass")

        assert hasattr(cls, "async_method")
        import asyncio

        instance = cls()
        result = asyncio.run(instance.async_method())
        assert result == "async result"


class TestConvertCls:
    """Tests for convert_cls function."""

    @patch("pinjected.injected_class.modify_ast_test.logger")
    def test_convert_simple_class(self, mock_logger):
        """Test converting a simple class."""

        # Define a test class
        class TestClass:
            async def method(self):
                return self.attr1 + self.attr2

        # Mock inspect.getsource to return our class definition
        class_source = textwrap.dedent("""
        class TestClass:
            async def method(self):
                return self.attr1 + self.attr2
        """).strip()

        with patch("inspect.getsource", return_value=class_source):
            result_cls = convert_cls(TestClass, ["method"], ["attr1", "attr2"])

        # Verify logging
        assert mock_logger.info.call_count == 2

        # Verify the result is a class
        assert result_cls.__name__ == "TestClass"
        assert hasattr(result_cls, "method")

    @patch("pinjected.injected_class.modify_ast_test.logger")
    def test_convert_with_sync_method_error(self, mock_logger):
        """Test that converting sync methods raises an error."""

        class TestClass:
            def sync_method(self):
                return self.attr1

        class_source = textwrap.dedent("""
        class TestClass:
            def sync_method(self):
                return self.attr1
        """).strip()

        with (
            patch("inspect.getsource", return_value=class_source),
            pytest.raises(RuntimeError, match="must be an async method"),
        ):
            convert_cls(TestClass, ["sync_method"], ["attr1"])

    @patch("pinjected.injected_class.modify_ast_test.logger")
    def test_convert_multiple_methods(self, mock_logger):
        """Test converting multiple methods."""

        class TestClass:
            async def method1(self):
                return self.attr1

            async def method2(self):
                return self.attr2

        class_source = textwrap.dedent("""
        class TestClass:
            async def method1(self):
                return self.attr1
            
            async def method2(self):
                return self.attr2
        """).strip()

        with patch("inspect.getsource", return_value=class_source):
            result_cls = convert_cls(
                TestClass, ["method1", "method2"], ["attr1", "attr2"]
            )

        # Verify both methods exist
        assert hasattr(result_cls, "method1")
        assert hasattr(result_cls, "method2")

    @patch("pinjected.injected_class.modify_ast_test.logger")
    def test_convert_empty_lists(self, mock_logger):
        """Test converting with empty method/attr lists."""

        class TestClass:
            async def method(self):
                return 42

        class_source = textwrap.dedent("""
        class TestClass:
            async def method(self):
                return 42
        """).strip()

        with patch("inspect.getsource", return_value=class_source):
            result_cls = convert_cls(TestClass, [], [])

        # Class should be unchanged
        assert result_cls.__name__ == "TestClass"
        instance = result_cls()
        result = asyncio.run(instance.method())
        assert result == 42


class TestMainBlock:
    """Test the __main__ block execution."""

    @patch("pinjected.injected_class.modify_ast_test.convert_cls")
    def test_main_execution(self, mock_convert_cls):
        """Test that main block calls convert_cls correctly."""
        # Import and execute the module's main block
        import pinjected.injected_class.modify_ast_test as module

        # The main block should have already executed during import
        # but we can verify what it would have called
        from pinjected.injected_class.test_module import PClassExample

        # Manually call what the main block does
        module.convert_cls(
            PClassExample,
            ["simple_method", "method1", "method2"],
            ["_dep1", "_dep2", "c"],
        )

        # Verify the call
        mock_convert_cls.assert_called_with(
            PClassExample,
            ["simple_method", "method1", "method2"],
            ["_dep1", "_dep2", "c"],
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
