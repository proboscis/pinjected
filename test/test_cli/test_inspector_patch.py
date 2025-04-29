import subprocess
import sys


def test_command_without_arguments():
    """Test that pinjected command without arguments shows help text instead of an error."""
    python_executable = sys.executable

    result = subprocess.run(
        [python_executable, "-m", "pinjected"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, "Command should exit with code 0"

    assert "Available commands:" in result.stdout, (
        "Help text should include 'Available commands:'"
    )
    assert "run" in result.stdout, "Help text should mention 'run' command"
    assert "describe" in result.stdout, "Help text should mention 'describe' command"

    assert "TypeError" not in result.stderr, "No TypeError should be displayed"
    assert "Inspector.__init__" not in result.stderr, (
        "No Inspector init error should be displayed"
    )
    assert "theme_name" not in result.stderr, "No theme_name error should be displayed"
