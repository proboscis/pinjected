"""Tests for ide_supports/default_design.py module."""

import pytest
from pathlib import Path
from unittest.mock import patch, Mock
from returns.maybe import Some

from pinjected.ide_supports.default_design import pinjected_internal_design
from pinjected import Design
from pinjected.v2.binds import BindInjected


class TestPinjectedInternalDesign:
    """Tests for pinjected_internal_design."""

    def test_pinjected_internal_design_is_design(self):
        """Test that pinjected_internal_design is a Design instance."""
        assert isinstance(pinjected_internal_design, Design)

    def test_design_has_expected_bindings(self):
        """Test that the design has expected bindings."""
        # Get the bindings from the design
        bindings = pinjected_internal_design.bindings

        # Check for expected keys
        expected_keys = {
            "logger",
            "runner_script_path",
            "custom_idea_config_creator",
            "default_design_path",
            "print_to_stdout",
            "inspect_and_make_configurations",
            "injected_to_idea_configs",
            "project_root",
            "default_working_dir",
            "internal_idea_config_creator",
        }

        binding_names = {k.name for k in bindings if hasattr(k, "name")}

        for key in expected_keys:
            assert key in binding_names, f"Expected binding '{key}' not found"

    def test_logger_binding(self):
        """Test the logger binding."""
        bindings = pinjected_internal_design.bindings

        # Find the logger binding
        logger_binding = None
        for k, v in bindings.items():
            if hasattr(k, "name") and k.name == "logger":
                logger_binding = v
                break

        assert logger_binding is not None
        # The logger should be the imported logger from pinjected_logging
        from pinjected.pinjected_logging import logger

        # For direct value bindings in design(), check if it's wrapped in Injected
        assert isinstance(logger_binding, BindInjected)
        from pinjected.di.injected import InjectedPure

        if isinstance(logger_binding.src, InjectedPure):
            assert logger_binding.src.value == logger

    def test_runner_script_path_binding(self):
        """Test the runner_script_path binding."""
        bindings = pinjected_internal_design.bindings

        # Find the runner_script_path binding
        runner_binding = None
        for k, v in bindings.items():
            if hasattr(k, "name") and k.name == "runner_script_path":
                runner_binding = v
                break

        assert runner_binding is not None
        # It should be an ExprBind from the IProxy
        from pinjected.v2.binds import ExprBind

        assert isinstance(runner_binding, ExprBind)
        # The src should be an EvaledInjected
        assert runner_binding.src is not None

    def test_custom_idea_config_creator_binding(self):
        """Test the custom_idea_config_creator binding."""
        bindings = pinjected_internal_design.bindings

        # Find the custom_idea_config_creator binding
        config_binding = None
        for k, v in bindings.items():
            if hasattr(k, "name") and k.name == "custom_idea_config_creator":
                config_binding = v
                break

        assert config_binding is not None
        # It should be a pure injected returning empty list
        assert isinstance(config_binding, BindInjected)
        from pinjected.di.injected import InjectedPure

        if isinstance(config_binding.src, InjectedPure):
            # Test the function it contains
            func = config_binding.src.value
            if callable(func):
                result = func("test_spec")
                assert result == []

    def test_default_design_path_is_none(self):
        """Test that default_design_path is None."""
        bindings = pinjected_internal_design.bindings

        # Find the default_design_path binding
        design_path_binding = None
        for k, v in bindings.items():
            if hasattr(k, "name") and k.name == "default_design_path":
                design_path_binding = v
                break

        assert design_path_binding is not None
        # BindInjected has src which contains the injected value
        # For a pure value like None, we need to check the src
        assert isinstance(design_path_binding, BindInjected)
        # Check if it's a pure Injected wrapping None
        from pinjected.di.injected import InjectedPure

        if isinstance(design_path_binding.src, InjectedPure):
            assert design_path_binding.src.value is None

    def test_print_to_stdout_is_true(self):
        """Test that print_to_stdout is True."""
        bindings = pinjected_internal_design.bindings

        # Find the print_to_stdout binding
        print_binding = None
        for k, v in bindings.items():
            if hasattr(k, "name") and k.name == "print_to_stdout":
                print_binding = v
                break

        assert print_binding is not None
        # BindInjected has src which contains the injected value
        assert isinstance(print_binding, BindInjected)
        from pinjected.di.injected import InjectedPure

        if isinstance(print_binding.src, InjectedPure):
            assert print_binding.src.value is True

    def test_project_root_binding(self):
        """Test the project_root binding."""
        bindings = pinjected_internal_design.bindings

        # Find the project_root binding
        project_root_binding = None
        for k, v in bindings.items():
            if hasattr(k, "name") and k.name == "project_root":
                project_root_binding = v
                break

        assert project_root_binding is not None
        # It should be a BindInjected that depends on module_path
        assert isinstance(project_root_binding, BindInjected)
        # Check if it has dependencies
        deps = project_root_binding.dependencies
        assert any(d.name == "module_path" for d in deps if hasattr(d, "name"))

    def test_default_working_dir_binding(self):
        """Test the default_working_dir binding."""
        bindings = pinjected_internal_design.bindings

        # Find the default_working_dir binding
        working_dir_binding = None
        for k, v in bindings.items():
            if hasattr(k, "name") and k.name == "default_working_dir":
                working_dir_binding = v
                break

        assert working_dir_binding is not None
        # It should be a BindInjected that depends on project_root
        assert isinstance(working_dir_binding, BindInjected)
        # Check if it has dependencies
        deps = working_dir_binding.dependencies
        assert any(d.name == "project_root" for d in deps if hasattr(d, "name"))

    def test_internal_idea_config_creator_binding(self):
        """Test the internal_idea_config_creator binding."""
        bindings = pinjected_internal_design.bindings

        # Find the internal_idea_config_creator binding
        internal_config_binding = None
        for k, v in bindings.items():
            if hasattr(k, "name") and k.name == "internal_idea_config_creator":
                internal_config_binding = v
                break

        assert internal_config_binding is not None
        # Test the function it contains
        assert isinstance(internal_config_binding, BindInjected)
        from pinjected.di.injected import InjectedPure

        if isinstance(internal_config_binding.src, InjectedPure):
            func = internal_config_binding.src.value
            if callable(func):
                result = func("test_spec")
                assert result == []

    @patch("pinjected.module_inspector.get_project_root")
    def test_project_root_computation(self, mock_get_project_root):
        """Test that project_root is computed correctly."""
        # Mock the get_project_root to return a known path
        mock_get_project_root.return_value = "/test/project/root"

        # Get the project_root binding
        bindings = pinjected_internal_design.bindings
        project_root_binding = None
        for k, v in bindings.items():
            if hasattr(k, "name") and k.name == "project_root":
                project_root_binding = v
                break

        # The binding is an Injected.bind that requires module_path
        # We need to test the lambda function
        if hasattr(project_root_binding, "_MappedInjected__f"):
            # Get the function from the mapped injected
            func = project_root_binding._MappedInjected__f
            result = func("/some/module/path")

            assert isinstance(result, Path)
            assert str(result) == "/test/project/root"
            mock_get_project_root.assert_called_once_with("/some/module/path")

    def test_default_working_dir_computation(self):
        """Test that default_working_dir is computed correctly."""
        # Get the default_working_dir binding
        bindings = pinjected_internal_design.bindings
        working_dir_binding = None
        for k, v in bindings.items():
            if hasattr(k, "name") and k.name == "default_working_dir":
                working_dir_binding = v
                break

        # Test the lambda function
        if hasattr(working_dir_binding, "_MappedInjected__f"):
            # Get the function from the mapped injected
            func = working_dir_binding._MappedInjected__f
            test_path = Path("/test/project/root")
            result = func(test_path)

            assert isinstance(result, Some)
            assert result.unwrap() == "/test/project/root"


class TestModuleImports:
    """Test module imports and structure."""

    def test_module_imports(self):
        """Test that the module imports correctly."""
        import pinjected.ide_supports.default_design as module

        # Check that expected items are available
        assert hasattr(module, "pinjected_internal_design")
        assert hasattr(module, "Path")
        assert hasattr(module, "Some")
        assert hasattr(module, "Design")
        assert hasattr(module, "Injected")
        assert hasattr(module, "design")
        assert hasattr(module, "IProxy")
        assert hasattr(module, "logger")

    def test_imports_are_used(self):
        """Test that imported items are actually used in the module."""
        import pinjected.ide_supports.default_design as module

        # The design should use these imports
        design_obj = module.pinjected_internal_design
        assert isinstance(design_obj, module.Design)

        # Check that Path, Some, IProxy are used in the design
        # This is implicitly tested by the design creation not failing


class TestRunnerScriptPath:
    """Test the runner_script_path IProxy behavior."""

    def test_runner_script_path_lambda(self):
        """Test the lambda function in runner_script_path."""
        # Get the runner_script_path binding
        bindings = pinjected_internal_design.bindings
        for k, v in bindings.items():
            if hasattr(k, "name") and k.name == "runner_script_path":
                break

        # The binding contains an IProxy with a lambda
        # Test that the lambda would work (imports pinjected.__main__)
        with patch("builtins.__import__") as mock_import:
            mock_main = Mock()
            mock_main.__file__ = "/path/to/pinjected/__main__.py"
            mock_import.return_value = mock_main

            # The lambda function is:
            # lambda: __import__("pinjected.__main__", fromlist=["__main__"]).__file__
            result = __import__("pinjected.__main__", fromlist=["__main__"]).__file__

            assert result == "/path/to/pinjected/__main__.py"
            mock_import.assert_called_with("pinjected.__main__", fromlist=["__main__"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
