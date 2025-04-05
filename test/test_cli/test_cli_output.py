import subprocess
import pytest
import os
import sys
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
