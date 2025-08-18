"""Simple tests for graph_inspection.py module."""

import pytest
from unittest.mock import Mock, patch
from dataclasses import is_dataclass

from pinjected.graph_inspection import (
    default_get_arg_names_from_class_name,
    find_classes,
    DIGraphHelper,
    _get_explicit_or_default_modules,
    _find_classes_in_module,
)
from pinjected.v2.binds import BindInjected, ExprBind
from pinjected.v2.keys import StrBindKey, DestructorKey
from pinjected.di.injected import Injected


class TestDefaultGetArgNamesFromClassName:
    """Test the default_get_arg_names_from_class_name function."""

    def test_simple_camel_case(self):
        """Test converting simple CamelCase to snake_case."""
        assert default_get_arg_names_from_class_name("FooBar") == ["foo_bar"]
        assert default_get_arg_names_from_class_name("MyClass") == ["my_class"]
        # All-caps abbreviations don't match the regex pattern
        assert default_get_arg_names_from_class_name("HTTPServer") == []
        # But CamelCase versions do
        assert default_get_arg_names_from_class_name("HttpServer") == ["http_server"]

    def test_with_leading_underscore(self):
        """Test converting class names with leading underscore."""
        assert default_get_arg_names_from_class_name("_FooBar") == ["foo_bar"]
        assert default_get_arg_names_from_class_name("_PrivateClass") == [
            "private_class"
        ]

    def test_single_word(self):
        """Test converting single word class names."""
        assert default_get_arg_names_from_class_name("Foo") == ["foo"]
        assert default_get_arg_names_from_class_name("_Bar") == ["bar"]

    def test_invalid_names(self):
        """Test with names that don't match pattern."""
        assert default_get_arg_names_from_class_name("lowercase") == []
        assert default_get_arg_names_from_class_name("123Numbers") == []
        assert default_get_arg_names_from_class_name("") == []


class TestFindClasses:
    """Test the find_classes function and related helpers."""

    def test_get_explicit_or_default_modules_none(self):
        """Test _get_explicit_or_default_modules with None."""
        assert _get_explicit_or_default_modules(None) == []

    def test_get_explicit_or_default_modules_list(self):
        """Test _get_explicit_or_default_modules with list."""
        modules = [Mock(), Mock()]
        assert _get_explicit_or_default_modules(modules) == modules

    @patch("pinjected.graph_inspection.inspect.getmembers")
    def test_find_classes_in_module(self, mock_getmembers):
        """Test _find_classes_in_module function."""

        class TestClass1:
            pass

        class TestClass2:
            pass

        mock_getmembers.return_value = [
            ("TestClass1", TestClass1),
            ("TestClass2", TestClass2),
            ("some_function", lambda: None),
            ("__class__", type),  # Should be ignored
        ]

        module = Mock()
        classes = _find_classes_in_module(module)

        assert TestClass1 in classes
        assert TestClass2 in classes
        assert len(classes) == 2

    @patch("pinjected.graph_inspection._find_classes_in_module")
    def test_find_classes_with_explicit_classes(self, mock_find_in_module):
        """Test find_classes with explicit classes provided."""

        class ExplicitClass:
            pass

        modules = [Mock()]
        explicit_classes = [ExplicitClass]
        mock_find_in_module.return_value = set()

        result = find_classes(modules, explicit_classes)

        assert ExplicitClass in result
        mock_find_in_module.assert_called_once()

    def test_find_classes_with_none_module(self):
        """Test find_classes handles None modules."""
        modules = [None, Mock()]
        result = find_classes(modules, None)

        # Should not raise exception
        assert isinstance(result, set)


class TestDIGraphHelper:
    """Test the DIGraphHelper dataclass."""

    def test_digraph_helper_is_dataclass(self):
        """Test that DIGraphHelper is a dataclass."""
        assert is_dataclass(DIGraphHelper)

    def test_digraph_helper_init(self):
        """Test DIGraphHelper initialization."""
        mock_design = Mock()
        helper = DIGraphHelper(src=mock_design)

        assert helper.src is mock_design
        assert helper.use_implicit_bindings is True

    def test_get_explicit_mapping(self):
        """Test get_explicit_mapping method."""
        mock_design = Mock()
        mock_design.bindings = {"key1": "bind1", "key2": "bind2"}

        helper = DIGraphHelper(src=mock_design)
        result = helper.get_explicit_mapping()

        assert result == {"key1": "bind1", "key2": "bind2"}

    @patch("pinjected.di.implicit_globals.IMPLICIT_BINDINGS", {"implicit": "binding"})
    def test_total_bindings_with_implicit(self):
        """Test total_bindings with implicit bindings enabled."""
        mock_design = Mock()
        mock_design.bindings = {"explicit": "binding"}

        helper = DIGraphHelper(src=mock_design, use_implicit_bindings=True)
        result = helper.total_bindings()

        assert "implicit" in result
        assert "explicit" in result

    def test_total_bindings_without_implicit(self):
        """Test total_bindings with implicit bindings disabled."""
        mock_design = Mock()
        mock_design.bindings = {"explicit": "binding"}

        helper = DIGraphHelper(src=mock_design, use_implicit_bindings=False)
        result = helper.total_bindings()

        assert "implicit" not in result
        assert result == {"explicit": "binding"}

    def test_total_mappings_with_bind_injected(self):
        """Test total_mappings with BindInjected."""
        mock_design = Mock()
        mock_injected = Mock(spec=Injected)
        mock_design.bindings = {StrBindKey("test"): BindInjected(mock_injected)}

        helper = DIGraphHelper(src=mock_design, use_implicit_bindings=False)
        result = helper.total_mappings()

        assert result["test"] is mock_injected

    def test_total_mappings_with_expr_bind(self):
        """Test total_mappings with ExprBind."""
        from pinjected.di.app_injected import EvaledInjected
        from pinjected.di.expr_util import Object
        from pinjected.di.injected import InjectedPure

        # Create a mock EvaledInjected that will work with ExprBind
        mock_value = InjectedPure(42)
        mock_ast = Object("test")
        evaled = Mock(spec=EvaledInjected)
        evaled.value = mock_value
        evaled.ast = mock_ast

        mock_design = Mock()
        mock_design.bindings = {StrBindKey("test"): ExprBind(src=evaled)}

        helper = DIGraphHelper(src=mock_design, use_implicit_bindings=False)
        result = helper.total_mappings()

        # ExprBind returns the src, so we expect the evaled injected
        assert result["test"] is evaled

    def test_total_mappings_with_destructor_key(self):
        """Test total_mappings ignores DestructorKey."""
        mock_design = Mock()
        mock_design.bindings = {DestructorKey("test"): Mock()}

        helper = DIGraphHelper(src=mock_design, use_implicit_bindings=False)
        result = helper.total_mappings()

        assert "test" not in result
        assert len(result) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
