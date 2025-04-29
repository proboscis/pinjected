import os
import subprocess
import sys


def test_list_command_exists():
    """Test that the list command is available in the CLI."""
    from pinjected.main_impl import PinjectedCLI
    
    cli = PinjectedCLI()
    
    assert hasattr(cli, 'list'), "The 'list' command should be available in CLI"
    list_impl = cli.list
    assert callable(list_impl), "The 'list' command should be callable"


def test_list_command_help():
    """Test that the list command has help information."""
    from pinjected.main_impl import list
    
    assert list.__doc__ is not None, "The 'list' command should have documentation"
    assert "List all IProxy objects" in list.__doc__, "The 'list' command documentation should explain its purpose"


def test_list_command_in_cli_help():
    """Test that the list command is visible in CLI help text."""
    from pinjected.main_impl import PinjectedCLI
    
    cli = PinjectedCLI()
    help_text = cli.__doc__ or ""
    
    assert "list" in help_text, "The 'list' command should be visible in CLI help text"
    assert hasattr(cli, 'list'), "The 'list' command should be registered in CLI"


def test_list_command_error_without_module_path():
    """Test that the list command shows an error when no module path is provided."""
    python_executable = sys.executable
    
    result = subprocess.run(
        [python_executable, "-m", "pinjected", "list"],
        capture_output=True,
        text=True,
        check=False,
        env=dict(os.environ, PYTHONPATH=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    )
    
    assert "Error: You must provide a module path" in result.stdout, \
        "The list command should show an error when no module path is provided"
    assert "Examples:" in result.stdout, \
        "The list command should show examples when no module path is provided"
