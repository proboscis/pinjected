import subprocess
import pytest
import os
import sys
import re
from unittest.mock import patch


def test_commands_in_module_output():
    """Test that commands are visible when running 'python -m pinjected'."""
    from pinjected.main_impl import PinjectedCLI
    
    cli = PinjectedCLI()
    
    assert hasattr(cli, 'run'), "The 'run' command should be available in CLI"
    assert hasattr(cli, 'describe'), "The 'describe' command should be available in CLI"
    
    run_impl = getattr(cli, 'run')
    describe_impl = getattr(cli, 'describe')
    assert callable(run_impl), "The 'run' command should be callable"
    assert callable(describe_impl), "The 'describe' command should be callable"


@pytest.mark.asyncio
async def test_command_help_documentation():
    """Test that command help documentation is properly set up."""
    from pinjected.main_impl import run, describe
    
    assert run.__doc__ is not None, "The 'run' command should have documentation"
    assert "load the injected variable" in run.__doc__, "The 'run' command documentation should explain its purpose"
    
    assert describe.__doc__ is not None, "The 'describe' command should have documentation"
    assert "human-readable description" in describe.__doc__, "The 'describe' command documentation should explain its purpose"


def test_cli_command_visibility_with_subprocess():
    """Test that commands are visible when running the CLI with subprocess."""
    from pinjected.main_impl import PinjectedCLI
    
    cli = PinjectedCLI()
    help_text = cli.__doc__ or ""
    
    assert "run " in help_text, "The 'run' command should be visible in CLI help text"
    assert "describe " in help_text, "The 'describe' command should be visible in CLI help text"


def test_run_command_help_with_subprocess():
    """Test that the 'run' command help is accessible."""
    from pinjected.main_impl import run
    
    help_text = run.__doc__ or ""
    
    assert "var_path" in help_text, "The 'run' command help should mention var_path parameter"
    assert "design_path" in help_text, "The 'run' command help should mention design_path parameter"


def test_describe_command_help_with_subprocess():
    """Test that the 'describe' command help is accessible."""
    from pinjected.main_impl import describe
    
    help_text = describe.__doc__ or ""
    
    assert "var_path" in help_text, "The 'describe' command help should mention var_path parameter"
    assert "design_path" in help_text, "The 'describe' command help should mention design_path parameter"


def test_command_visibility_in_module():
    """Test that commands are visible when importing the module."""
    import importlib
    
    try:
        main_impl = importlib.import_module("pinjected.main_impl")
        
        assert hasattr(main_impl, "main"), "The main_impl module should have a main function"
        
        assert hasattr(main_impl, "run"), "The 'run' command should be available in main_impl"
        assert hasattr(main_impl, "describe"), "The 'describe' command should be available in main_impl"
        
        assert callable(main_impl.run), "The 'run' command should be callable"
        assert callable(main_impl.describe), "The 'describe' command should be callable"
        
        main_module = importlib.import_module("pinjected.__main__")
    except ImportError as e:
        pytest.fail(f"Failed to import pinjected module: {e}")
    except Exception as e:
        pytest.fail(f"Unexpected error when testing module imports: {e}")
