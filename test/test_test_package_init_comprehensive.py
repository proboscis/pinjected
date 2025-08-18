"""Comprehensive tests for test_package/__init__.py module."""

import pytest
from unittest.mock import Mock

from pinjected.test_package import (
    dummy_config_creator_for_test,
    run_test_module,
    __design__,
)


class TestTestPackageInit:
    """Test the test_package initialization module."""

    def test_dummy_config_creator_is_injected(self):
        """Test that dummy_config_creator_for_test is an injected function."""
        from pinjected.di.partially_injected import Partial

        assert isinstance(dummy_config_creator_for_test, Partial)

    def test_dummy_config_creator_function(self):
        """Test the dummy_config_creator_for_test function logic."""
        # Get the underlying function
        func = dummy_config_creator_for_test.src_function

        # Create mocks
        mock_logger = Mock()
        mock_tgt = Mock()
        mock_tgt.name = "test_target"

        # Call the function with positional arguments (note the / in the function signature)
        result = func(
            "/path/to/runner",  # runner_script_path
            "/usr/bin/python",  # interpreter_path
            Mock(value_or=Mock(return_value="/working/dir")),  # default_working_dir
            mock_logger,  # logger
            mock_tgt,  # tgt
        )

        # Verify logger was called
        mock_logger.info.assert_called_once()
        assert "custom config creator called" in mock_logger.info.call_args[0][0]

        # Verify result
        assert isinstance(result, list)
        assert len(result) == 1

        config = result[0]
        assert config.name == "dummy for test_package.child.__init__"
        assert config.script_path == "/path/to/runner"
        assert config.interpreter_path == "/usr/bin/python"
        assert config.arguments == []
        assert config.working_dir == "/working/dir"

    def test_run_test_module_is_iproxy(self):
        """Test that run_test_module is an IProxy."""
        # run_test_module is created with Injected.bind() which returns InjectedFromFunction
        from pinjected.di.injected import InjectedFromFunction

        assert isinstance(run_test_module, InjectedFromFunction)

    def test_design_configuration(self):
        """Test the __design__ configuration."""
        assert __design__ is not None

        # Check design properties
        # The design has StrBindKey objects as keys
        from pinjected.v2.keys import StrBindKey

        assert StrBindKey("custom_idea_config_creator") in __design__
        # The value is wrapped in a binding
        binding = __design__[StrBindKey("custom_idea_config_creator")]
        assert binding is not None

    def test_module_imports(self):
        """Test that the module imports correctly."""
        from pinjected import test_package

        # Check imports from pinjected
        assert hasattr(test_package, "injected")
        assert hasattr(test_package, "design")
        assert hasattr(test_package, "Injected")
        assert hasattr(test_package, "IProxy")

        # Check specific imports
        assert hasattr(test_package, "IdeaRunConfiguration")
        assert hasattr(test_package, "ModuleVarSpec")
        assert hasattr(test_package, "test_tree")

    def test_module_exports(self):
        """Test module exports."""
        import pinjected.test_package as pkg

        # Check main exports
        assert hasattr(pkg, "dummy_config_creator_for_test")
        assert hasattr(pkg, "run_test_module")
        assert hasattr(pkg, "__design__")

    def test_japanese_comment(self):
        """Test that the module contains Japanese comments."""
        import inspect
        import pinjected.test_package

        source = inspect.getsource(pinjected.test_package)
        # Check for Japanese comment
        assert "非同期関数" in source


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
