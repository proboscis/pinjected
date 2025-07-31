"""Simple tests for test_package/__init__.py module."""

import pytest
from unittest.mock import Mock
from returns.maybe import Some

from pinjected import test_package


class TestTestPackageInit:
    """Test the test_package/__init__ module functionality."""

    def test_module_imports(self):
        """Test that the module has expected imports."""
        assert hasattr(test_package, "injected")
        assert hasattr(test_package, "design")
        assert hasattr(test_package, "IProxy")
        assert hasattr(test_package, "Injected")

    def test_dummy_config_creator_exists(self):
        """Test that dummy_config_creator_for_test is defined."""
        assert hasattr(test_package, "dummy_config_creator_for_test")
        from pinjected.di.partially_injected import Partial

        assert isinstance(test_package.dummy_config_creator_for_test, Partial)

    def test_run_test_module_exists(self):
        """Test that run_test_module IProxy is defined."""
        assert hasattr(test_package, "run_test_module")
        # run_test_module is an InjectedFromFunction
        from pinjected.di.injected import InjectedFromFunction

        assert isinstance(test_package.run_test_module, InjectedFromFunction)

    def test_design_exists(self):
        """Test that __design__ is defined."""
        assert hasattr(test_package, "__design__")
        # Just check it's a Design object
        from pinjected import Design

        assert isinstance(test_package.__design__, Design)

    def test_dummy_config_creator_function(self):
        """Test the dummy_config_creator_for_test function logic."""
        # Get the underlying function
        config_creator = test_package.dummy_config_creator_for_test.src_function

        # Mock dependencies
        mock_logger = Mock()
        runner_script_path = "/path/to/runner"
        interpreter_path = "/path/to/python"
        default_working_dir = Some("/working/dir")

        # Create a proper ModuleVarSpec with all required attributes
        from dataclasses import dataclass

        @dataclass
        class MockModuleVarSpec:
            module: str
            name: str

        tgt = MockModuleVarSpec(module="test.module", name="var")

        # Call the function
        result = config_creator(
            runner_script_path, interpreter_path, default_working_dir, mock_logger, tgt
        )

        # Check logger was called
        mock_logger.info.assert_called_once_with("custom config creator called")

        # Check result
        assert len(result) == 1
        config = result[0]
        assert config.name == "dummy for test_package.child.__init__"
        assert config.script_path == runner_script_path
        assert config.interpreter_path == interpreter_path
        assert config.arguments == []
        assert config.working_dir == "/working/dir"

    def test_dummy_config_creator_with_no_working_dir(self):
        """Test dummy_config_creator_for_test with None working dir."""
        config_creator = test_package.dummy_config_creator_for_test.src_function

        # Mock dependencies with Nothing for working dir
        from returns.maybe import Nothing

        mock_logger = Mock()
        runner_script_path = "/path/to/runner"
        interpreter_path = "/path/to/python"
        default_working_dir = Nothing

        # Create a proper ModuleVarSpec with all required attributes
        from dataclasses import dataclass

        @dataclass
        class MockModuleVarSpec:
            module: str
            name: str

        tgt = MockModuleVarSpec(module="test.module", name="var")

        # Call the function
        result = config_creator(
            runner_script_path, interpreter_path, default_working_dir, mock_logger, tgt
        )

        # Check working_dir defaults to "."
        assert result[0].working_dir == "."

    def test_idea_run_configuration_structure(self):
        """Test that IdeaRunConfiguration is properly imported."""
        from pinjected.helper_structure import IdeaRunConfiguration

        # Create an instance to verify structure
        config = IdeaRunConfiguration(
            name="test",
            script_path="/path",
            interpreter_path="/python",
            arguments=[],
            working_dir=".",
        )

        assert config.name == "test"
        assert config.script_path == "/path"
        assert config.interpreter_path == "/python"
        assert config.arguments == []
        assert config.working_dir == "."


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
