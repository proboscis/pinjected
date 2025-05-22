"""Test module for the 'resolve' alias to the 'run' command."""

from pinjected.main_impl import PinjectedCLI


def test_resolve_alias_exists() -> None:
    """Test that the 'resolve' command is registered as an alias to 'run' in the PinjectedCLI class."""
    cli = PinjectedCLI()
    assert hasattr(cli, "resolve"), (
        "The 'resolve' command should be registered in PinjectedCLI"
    )
    assert cli.resolve == cli.run, (
        "The 'resolve' command should be an alias to the 'run' command"
    )


def test_resolve_alias_in_help() -> None:
    """Test that the 'resolve' command is visible in the CLI help output."""
    cli = PinjectedCLI()
    help_text = cli.__doc__ or ""

    assert "resolve" in help_text, (
        "The 'resolve' command should be visible in the help output"
    )
