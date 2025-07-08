"""Tests for graph_inspection module."""

import pytest
from types import ModuleType
from unittest.mock import Mock, patch
from pinjected.graph_inspection import (
    default_get_arg_names_from_class_name,
    find_classes,
    _get_explicit_or_default_modules,
    _find_classes_in_module,
    DIGraphHelper,
)
from pinjected.di.injected import Injected
from pinjected.v2.binds import BindInjected, ExprBind
from pinjected.v2.keys import StrBindKey, DestructorKey


class TestDefaultGetArgNamesFromClassName:
    """Test default_get_arg_names_from_class_name function."""

    def test_camel_case_conversion(self):
        """Test CamelCase to snake_case conversion."""
        assert default_get_arg_names_from_class_name("FooBar") == ["foo_bar"]
        assert default_get_arg_names_from_class_name("MyService") == ["my_service"]
        # HTTPClient doesn't match the pattern since it's all caps at the start
        assert default_get_arg_names_from_class_name("HttpClient") == ["http_client"]

    def test_single_word(self):
        """Test single word class names."""
        assert default_get_arg_names_from_class_name("Service") == ["service"]
        assert default_get_arg_names_from_class_name("Manager") == ["manager"]

    def test_leading_underscore(self):
        """Test class names with leading underscore."""
        assert default_get_arg_names_from_class_name("_FooBar") == ["foo_bar"]
        assert default_get_arg_names_from_class_name("_Service") == ["service"]

    def test_no_match(self):
        """Test when no CamelCase pattern matches."""
        assert default_get_arg_names_from_class_name("") == []
        assert default_get_arg_names_from_class_name("lowercase") == []
        assert default_get_arg_names_from_class_name("123ABC") == []

    def test_mixed_case(self):
        """Test mixed case patterns."""
        # The function expects CamelCase, not all caps at the start
        assert default_get_arg_names_from_class_name("XmlParser") == ["xml_parser"]
        assert default_get_arg_names_from_class_name("JsonData") == ["json_data"]


class TestFindClasses:
    """Test find_classes function."""

    def test_find_classes_with_explicit_classes(self):
        """Test find_classes when explicit classes are provided."""

        class ClassA:
            pass

        class ClassB:
            pass

        result = find_classes(modules=None, classes=[ClassA, ClassB])
        assert result == {ClassA, ClassB}

    def test_find_classes_with_modules(self):
        """Test find_classes with modules."""
        # Create a mock module
        module = ModuleType("test_module")

        class TestClass:
            pass

        module.TestClass = TestClass

        result = find_classes(modules=[module], classes=None)
        assert TestClass in result

    def test_find_classes_with_both(self):
        """Test find_classes with both modules and classes."""

        class ExplicitClass:
            pass

        module = ModuleType("test_module")

        class ModuleClass:
            pass

        module.ModuleClass = ModuleClass

        result = find_classes(modules=[module], classes=[ExplicitClass])
        assert ExplicitClass in result
        assert ModuleClass in result

    def test_find_classes_with_none_module(self):
        """Test find_classes handles None modules gracefully."""
        result = find_classes(modules=[None], classes=None)
        assert result == set()


class TestGetExplicitOrDefaultModules:
    """Test _get_explicit_or_default_modules function."""

    def test_none_modules(self):
        """Test with None modules."""
        assert _get_explicit_or_default_modules(None) == []

    def test_with_modules(self):
        """Test with actual modules."""
        modules = [ModuleType("test1"), ModuleType("test2")]
        assert _get_explicit_or_default_modules(modules) == modules


class TestFindClassesInModule:
    """Test _find_classes_in_module function."""

    def test_find_classes_in_module(self):
        """Test finding classes in a module."""
        module = ModuleType("test_module")

        class ClassA:
            pass

        class ClassB:
            pass

        def function():
            pass

        module.ClassA = ClassA
        module.ClassB = ClassB
        module.function = function
        module.variable = 42

        result = _find_classes_in_module(module)
        assert ClassA in result
        assert ClassB in result
        assert len(result) == 2

    def test_module_with_builtin_types(self):
        """Test finding classes with built-in types."""
        module = ModuleType("test_module")

        class UserClass:
            pass

        module.UserClass = UserClass
        module.int_type = int  # Built-in type
        module.str_type = str  # Built-in type

        result = _find_classes_in_module(module)

        # All classes including built-ins should be found
        assert UserClass in result
        assert int in result
        assert str in result


class TestDIGraphHelper:
    """Test DIGraphHelper class."""

    def test_instantiation(self):
        """Test DIGraphHelper instantiation."""
        mock_design = Mock()
        helper = DIGraphHelper(src=mock_design)
        assert helper.src is mock_design
        assert helper.use_implicit_bindings is True

        helper2 = DIGraphHelper(src=mock_design, use_implicit_bindings=False)
        assert helper2.use_implicit_bindings is False

    def test_get_explicit_mapping(self):
        """Test get_explicit_mapping method."""
        mock_design = Mock()
        mock_design.bindings = {"key1": "bind1", "key2": "bind2"}

        helper = DIGraphHelper(src=mock_design)
        result = helper.get_explicit_mapping()

        assert result == {"key1": "bind1", "key2": "bind2"}

    def test_total_mappings_with_bind_injected(self):
        """Test total_mappings with BindInjected."""
        mock_design = Mock()
        injected_obj = Injected.pure(lambda: "value")

        mock_design.bindings = {StrBindKey("test_key"): BindInjected(injected_obj)}

        helper = DIGraphHelper(src=mock_design, use_implicit_bindings=False)
        result = helper.total_mappings()

        assert "test_key" in result
        assert result["test_key"] == injected_obj

    def test_total_mappings_with_expr_bind(self):
        """Test total_mappings with ExprBind."""
        from pinjected.di.app_injected import EvaledInjected

        mock_design = Mock()
        # Create a proper EvaledInjected mock
        src_expr = Mock(spec=EvaledInjected)

        mock_design.bindings = {
            StrBindKey("expr_key"): ExprBind(src=src_expr, _metadata=None)
        }

        helper = DIGraphHelper(src=mock_design, use_implicit_bindings=False)
        result = helper.total_mappings()

        assert "expr_key" in result
        assert result["expr_key"] == src_expr

    def test_total_mappings_skips_destructor_key(self):
        """Test total_mappings skips DestructorKey."""
        mock_design = Mock()

        mock_design.bindings = {DestructorKey("destructor"): Mock()}

        helper = DIGraphHelper(src=mock_design, use_implicit_bindings=False)
        result = helper.total_mappings()

        assert len(result) == 0

    def test_total_mappings_unsupported_key_type(self):
        """Test total_mappings raises for unsupported key type."""
        mock_design = Mock()

        # Create a different key type
        unsupported_key = Mock()
        unsupported_key.__class__.__name__ = "UnsupportedKey"

        mock_design.bindings = {unsupported_key: Mock()}

        helper = DIGraphHelper(src=mock_design, use_implicit_bindings=False)

        with pytest.raises(ValueError) as exc_info:
            helper.total_mappings()

        assert "unsupported key type" in str(exc_info.value)

    @patch("pinjected.graph_inspection.logger")
    def test_total_bindings_with_implicit(self, mock_logger):
        """Test total_bindings with implicit bindings enabled."""
        mock_design = Mock()
        mock_design.bindings = {"explicit": "value"}

        with patch(
            "pinjected.di.implicit_globals.IMPLICIT_BINDINGS", {"implicit": "value"}
        ):
            helper = DIGraphHelper(src=mock_design, use_implicit_bindings=True)
            result = helper.total_bindings()

            assert "explicit" in result
            assert "implicit" in result
            assert result["explicit"] == "value"
            assert result["implicit"] == "value"

            # Check that logger was called
            mock_logger.debug.assert_called_once()
            assert "1 global implicit mappings" in mock_logger.debug.call_args[0][0]

    def test_total_bindings_without_implicit(self):
        """Test total_bindings with implicit bindings disabled."""
        mock_design = Mock()
        mock_design.bindings = {"explicit": "value"}

        helper = DIGraphHelper(src=mock_design, use_implicit_bindings=False)
        result = helper.total_bindings()

        assert result == {"explicit": "value"}

    def test_is_dataclass(self):
        """Test that DIGraphHelper is a dataclass."""
        from dataclasses import is_dataclass

        assert is_dataclass(DIGraphHelper)
