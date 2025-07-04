"""Test new CLI commands in IDE configurations."""

import sys
from pathlib import Path
from unittest.mock import Mock

from returns.maybe import Some

from pinjected import __main__, design
from pinjected.helper_structure import IdeaRunConfigurations
from pinjected.module_inspector import ModuleVarSpec
from pinjected.pinjected_logging import logger
from pinjected.test import injected_pytest
from pinjected.ide_supports.create_configs import injected_to_idea_configs, extract_args_for_runnable


# Create a test design with all required dependencies
test_design = design(
    interpreter_path=sys.executable,
    runner_script_path=__main__.__file__,
    default_design_paths=["test_design"],
    default_working_dir=Some("/test/dir"),
    custom_idea_config_creator=lambda x: [],
    internal_idea_config_creator=lambda x: [],
    extract_args_for_runnable=extract_args_for_runnable,
    logger=logger,
    injected_to_idea_configs=injected_to_idea_configs,
)


@injected_pytest(test_design)
def test_injected_to_idea_configs_includes_new_commands(injected_to_idea_configs):
    """Test that injected_to_idea_configs generates configurations for new CLI commands."""
    # Create a mock ModuleVarSpec
    mock_var = Mock()
    mock_var.__runnable_metadata__ = {"kind": "object"}
    
    tgt = ModuleVarSpec(
        var_path="test_module.test_var",
        module_file_path=Path("/test/module.py"),
        var=mock_var
    )
    
    # Call the injected function
    result = injected_to_idea_configs(tgt)
    
    # Check that we got IdeaRunConfigurations
    assert isinstance(result, IdeaRunConfigurations)
    assert "test_var" in result.configs
    
    # Get all configuration names
    config_names = [cfg.name for cfg in result.configs["test_var"]]
    
    # Check that new commands are present
    assert any("describe_json" in name for name in config_names), f"describe_json not found in {config_names}"
    assert any("trace" in name for name in config_names), f"trace not found in {config_names}"
    assert any("list module" in name for name in config_names), f"list module not found in {config_names}"
    
    # Check the command arguments
    for cfg in result.configs["test_var"]:
        if "describe_json" in cfg.name:
            assert cfg.arguments[0] == "describe-json", f"describe_json should use 'describe-json' command, got {cfg.arguments}"
            assert "test_var" in " ".join(cfg.arguments[1:]), f"describe_json should include variable path"
        elif "trace" in cfg.name and "test_var" in cfg.name:
            assert cfg.arguments[0] == "trace-key", f"trace should use 'trace-key' command, got {cfg.arguments}"
            assert cfg.arguments[1] == "test_var", f"trace should have variable name as second arg"
        elif "list module" in cfg.name:
            assert cfg.arguments[0] == "list", f"list should use 'list' command, got {cfg.arguments}"
            assert cfg.arguments[1] == "test_module", f"list should have module path"
            

@injected_pytest(test_design)
def test_all_configurations_have_valid_structure(injected_to_idea_configs):
    """Test that all generated configurations have the required structure."""
    # Create a mock ModuleVarSpec
    mock_var = Mock()
    mock_var.__runnable_metadata__ = {"kind": "callable"}
    
    tgt = ModuleVarSpec(
        var_path="mypackage.mymodule.my_function",
        module_file_path=Path("/test/mymodule.py"),
        var=mock_var
    )
    
    # Call the function
    result = injected_to_idea_configs(tgt)
    
    # Check all configurations
    for var_name, configs in result.configs.items():
        for cfg in configs:
            # All configs must have these fields
            assert cfg.name is not None and cfg.name != "", "Config must have a name"
            assert cfg.script_path is not None and cfg.script_path != "", "Config must have script_path"
            assert cfg.interpreter_path is not None and cfg.interpreter_path != "", "Config must have interpreter_path"
            assert cfg.arguments is not None and len(cfg.arguments) > 0, "Config must have arguments"
            assert cfg.working_dir is not None, "Config must have working_dir"
            
            # The script path should be consistent
            assert cfg.script_path.endswith("__main__.py") or cfg.script_path == "/path/to/runner.py", (
                f"Script path should be __main__.py or runner.py, got: {cfg.script_path}"
            )
            
            # Arguments should start with a valid command
            valid_commands = ["run", "call", "describe", "describe-json", "trace-key", "list", "run_injected"]
            assert cfg.arguments[0] in valid_commands, (
                f"First argument should be a valid command, got: {cfg.arguments[0]}"
            )


# Test with different designs for different module paths
@injected_pytest(test_design)
def test_list_command_uses_module_path(injected_to_idea_configs):
    """Test that the list command correctly extracts the module path."""
    # Test with different module paths
    test_cases = [
        ("mypackage.module1.var1", "mypackage.module1"),
        ("a.b.c.d.function_name", "a.b.c.d"),
        ("simple.var", "simple"),
    ]
    
    for var_path, expected_module in test_cases:
        mock_var = Mock()
        mock_var.__runnable_metadata__ = {"kind": "object"}
        
        tgt = ModuleVarSpec(
            var_path=var_path,
            module_file_path=Path(f"/{var_path.replace('.', '/')}.py"),
            var=mock_var
        )
        
        result = injected_to_idea_configs(tgt)
        
        # Find the list command configuration
        list_configs = [
            cfg for cfg in result.configs[var_path.split(".")[-1]]
            if cfg.arguments[0] == "list"
        ]
        
        assert len(list_configs) > 0, "Should have at least one list configuration"
        
        # Check that it uses the correct module path
        for cfg in list_configs:
            assert cfg.arguments[1] == expected_module, (
                f"Expected module path {expected_module}, got {cfg.arguments[1]}"
            )


# Test without metadata to verify the code handles that case
@injected_pytest(test_design + design(default_design_paths=["pinjected.EmptyDesign"]))
def test_handles_missing_metadata(injected_to_idea_configs):
    """Test that the function handles variables without __runnable_metadata__."""
    # Create a mock without metadata
    mock_var = Mock()
    # Don't set __runnable_metadata__
    
    tgt = ModuleVarSpec(
        var_path="test_module.test_var_no_meta",
        module_file_path=Path("/test/module.py"),
        var=mock_var
    )
    
    # This should not crash, but might skip the variable
    result = injected_to_idea_configs(tgt)
    
    # The function should return a valid IdeaRunConfigurations object
    assert isinstance(result, IdeaRunConfigurations)
    # It may or may not have configs for this variable depending on implementation
