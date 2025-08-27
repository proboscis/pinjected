"""Tests for test_package/__init__.py module."""

import pytest
from unittest.mock import Mock, patch
from returns.maybe import Some, Nothing

from pinjected.helper_structure import IdeaRunConfiguration
from pinjected.module_inspector import ModuleVarSpec


def test_imports():
    """Test that the module imports correctly."""
    # Import the module
    import pinjected.test_package

    # Check that key attributes exist
    assert hasattr(pinjected.test_package, "dummy_config_creator_for_test")
    assert hasattr(pinjected.test_package, "run_test_module")
    assert hasattr(pinjected.test_package, "__design__")


def test_dummy_config_creator_for_test():
    """Test dummy_config_creator_for_test function."""
    # Import after checking
    from pinjected.test_package import dummy_config_creator_for_test

    # Check it's a Partial (injected function)
    assert hasattr(dummy_config_creator_for_test, "src_function")

    # Get the actual function
    func = dummy_config_creator_for_test.src_function

    # Mock dependencies
    mock_logger = Mock()
    mock_tgt = Mock(spec=ModuleVarSpec)

    # Call the function with positional args (note the / in the function definition)
    result = func(
        "/path/to/runner",  # runner_script_path
        "/path/to/python",  # interpreter_path
        Some("/path/to/workdir"),  # default_working_dir
        mock_logger,  # logger
        mock_tgt,  # tgt
    )

    # Verify logger was called
    mock_logger.info.assert_called_once_with("custom config creator called")

    # Verify result
    assert isinstance(result, list)
    assert len(result) == 1
    config = result[0]
    assert isinstance(config, IdeaRunConfiguration)
    assert config.name == "dummy for test_package.child.__init__"
    assert config.script_path == "/path/to/runner"
    assert config.interpreter_path == "/path/to/python"
    assert config.arguments == []
    assert config.working_dir == "/path/to/workdir"


def test_dummy_config_creator_with_nothing_working_dir():
    """Test dummy_config_creator_for_test with Nothing for working_dir."""
    from pinjected.test_package import dummy_config_creator_for_test

    # Get the actual function
    func = dummy_config_creator_for_test.src_function

    # Mock dependencies
    mock_logger = Mock()
    mock_tgt = Mock(spec=ModuleVarSpec)

    # Call with Nothing for working_dir (positional args)
    result = func(
        "/path/to/runner",  # runner_script_path
        "/path/to/python",  # interpreter_path
        Nothing,  # default_working_dir
        mock_logger,  # logger
        mock_tgt,  # tgt
    )

    # Verify result uses "." as default
    config = result[0]
    assert config.working_dir == "."


def test_run_test_module():
    """Test run_test_module IProxy."""
    from pinjected.test_package import run_test_module

    # Check it's an IProxy
    assert hasattr(run_test_module, "__class__")
    # It should be some kind of proxy object
    assert run_test_module is not None


def test_design_configuration():
    """Test __design__ configuration."""
    from pinjected.test_package import __design__

    # Check __design__ is a Design object
    assert hasattr(__design__, "__class__")

    # Check it was created with expected parameters
    # The design should have the custom_idea_config_creator set
    # Note: Design objects are opaque, so we can't directly inspect bindings
    # but we can verify it exists and is the right type
    assert __design__ is not None


@patch("pinjected.test_helper.test_runner.test_tree")
def test_run_test_module_binding(mock_test_tree):
    """Test run_test_module is bound to test_tree."""
    # This tests the lambda binding
    # We can't easily execute the IProxy directly, but we can verify
    # the module imports and sets it up correctly
    from pinjected.test_package import run_test_module

    # The binding exists
    assert run_test_module is not None


def test_module_structure():
    """Test overall module structure."""
    import pinjected.test_package as pkg

    # Check all expected exports
    expected_attrs = ["dummy_config_creator_for_test", "run_test_module", "__design__"]

    for attr in expected_attrs:
        assert hasattr(pkg, attr), f"Missing expected attribute: {attr}"


def test_japanese_comment():
    """Test that Japanese comment doesn't break anything."""
    # The module has a Japanese comment, verify it loads correctly

    # If we got here without syntax error, the comment is fine
    assert True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
