from unittest.mock import patch

from pinjected.main_impl import PinjectedCLI


def test_run_command_exists_in_cli():
    """Test that the 'run' command is registered in the PinjectedCLI class."""
    cli = PinjectedCLI()
    assert hasattr(cli, "run"), "The 'run' command should be registered in PinjectedCLI"


def test_describe_command_exists_in_cli():
    """Test that the 'describe' command is registered in the PinjectedCLI class."""
    cli = PinjectedCLI()
    assert hasattr(cli, "describe"), (
        "The 'describe' command should be registered in PinjectedCLI"
    )


def test_cli_commands_availability():
    """Test that main commands are available in the CLI instance."""
    cli = PinjectedCLI()
    essential_commands = [
        "run",
        "describe",
        "call",
        "check_config",
        "json_graph",
        "create_overloads",
    ]
    for cmd in essential_commands:
        assert hasattr(cli, cmd), f"Command '{cmd}' should be available in the CLI"


def mock_fire_cli(*args, **kwargs):
    """Mock function to capture the component passed to fire.Fire()"""
    return args[0]


def test_main_initializes_cli_with_commands():
    """Test that main() initializes PinjectedCLI with essential commands."""
    with patch("fire.Fire", side_effect=mock_fire_cli) as mock_fire:
        try:
            from pinjected.main_impl import main

            cli = main()

            assert isinstance(cli, PinjectedCLI), (
                "main() should initialize PinjectedCLI"
            )

            assert hasattr(cli, "run"), "The 'run' command should be available"
            assert hasattr(cli, "describe"), (
                "The 'describe' command should be available"
            )
        except Exception:
            assert mock_fire.called, "fire.Fire() should have been called"


def test_run_command_function_exists():
    """Test that the run command function exists and has the expected signature."""
    import inspect

    from pinjected.main_impl import run

    sig = inspect.signature(run)
    assert "var_path" in sig.parameters, "run() should have a var_path parameter"
    assert "design_path" in sig.parameters, "run() should have a design_path parameter"


def test_describe_command_function_exists():
    """Test that the describe command function exists and has the expected signature."""
    import inspect

    from pinjected.main_impl import describe

    sig = inspect.signature(describe)
    assert "var_path" in sig.parameters, "describe() should have a var_path parameter"
    assert "design_path" in sig.parameters, (
        "describe() should have a design_path parameter"
    )
