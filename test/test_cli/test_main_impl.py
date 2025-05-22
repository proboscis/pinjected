from pinjected.main_impl import PinjectedCLI


def test_pinjected_cli_docstring():
    """Test that the PinjectedCLI class has the expected docstring."""
    cli = PinjectedCLI()

    assert "Pinjected: Python Dependency Injection Framework" in cli.__doc__
    assert "Available commands:" in cli.__doc__
    assert "run" in cli.__doc__
    assert "resolve" in cli.__doc__
    assert "check_config" in cli.__doc__
    assert "create_overloads" in cli.__doc__
    assert "json_graph" in cli.__doc__
    assert "describe" in cli.__doc__


def test_fire_help_output():
    """Test that the PinjectedCLI class has a comprehensive docstring for Fire help."""
    cli = PinjectedCLI()

    assert "Pinjected: Python Dependency Injection Framework" in cli.__doc__
    assert "Available commands:" in cli.__doc__
    assert "run" in cli.__doc__
    assert "resolve" in cli.__doc__
    assert "check_config" in cli.__doc__
    assert "create_overloads" in cli.__doc__
    assert "json_graph" in cli.__doc__
    assert "describe" in cli.__doc__
    assert "For more information on a specific command" in cli.__doc__
    assert "Example:" in cli.__doc__


def test_cli_command_visibility():
    """Test that essential commands are explicitly documented in the CLI help text."""
    cli = PinjectedCLI()

    help_text = cli.__doc__

    assert "run " in help_text, "The 'run' command should be visible in CLI help text"
    assert "describe " in help_text, (
        "The 'describe' command should be visible in CLI help text"
    )

    assert "Run an injected variable" in help_text, (
        "The 'run' command description should be in help text"
    )
    assert "Generate a human-readable description" in help_text, (
        "The 'describe' command description should be in help text"
    )


def test_describe_command_help():
    """Test that the describe command docstring mentions the required format and both usage options."""
    from pinjected.main_impl import describe

    assert "full.module.path.var.name" in describe.__doc__
    assert "This parameter is required" in describe.__doc__
    assert "must point to an importable variable" in describe.__doc__

    cli = PinjectedCLI()
    assert "describe my_module.path.var" in cli.__doc__
    assert "describe --var_path=my_module.path.var" in cli.__doc__
