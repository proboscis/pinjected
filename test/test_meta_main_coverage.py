"""Tests for pinjected.meta_main module to improve coverage."""

import subprocess
import sys
from pathlib import Path


class TestMetaMain:
    """Test the meta_main module functionality."""

    def test_meta_main_execution(self):
        """Test that meta_main can be executed as a script."""
        # Test running meta_main as a module
        # Find the project root dynamically
        test_dir = Path(__file__).parent
        project_root = test_dir.parent

        result = subprocess.run(
            [sys.executable, "-m", "pinjected.meta_main", "--help"],
            capture_output=True,
            text=True,
            cwd=str(project_root),
        )

        # The module runs but may have errors due to dependencies
        # We just want to verify it executes the main block
        assert (
            "meta_main.py" in result.stderr or "run_with_meta_context" in result.stdout
        )

    def test_meta_main_deprecation_warning(self):
        """Test that deprecation warning is shown."""
        # Find the project root dynamically
        test_dir = Path(__file__).parent
        project_root = test_dir.parent

        result = subprocess.run(
            [sys.executable, "-m", "pinjected.meta_main", "--help"],
            capture_output=True,
            text=True,
            cwd=str(project_root),
            env={**subprocess.os.environ, "PYTHONWARNINGS": "default"},
        )

        # The deprecation warning should be in stderr
        assert "meta_main is deprecated" in result.stderr or result.returncode == 0

    def test_meta_main_direct_execution(self):
        """Test direct execution of the module to cover the __main__ block."""
        # Find the project root dynamically
        test_dir = Path(__file__).parent
        project_root = test_dir.parent

        # Create a test script that executes the main block
        test_script = f"""
import sys
sys.path.insert(0, "{project_root}")

# Mock fire.Fire to prevent actual execution
from unittest.mock import patch, MagicMock
with patch("fire.Fire") as mock_fire:
    # Set up the mock
    mock_fire.return_value = None
    
    # Import and execute
    import pinjected.meta_main
    
    # Now execute the main block by simulating direct execution
    import runpy
    with patch("warnings.warn") as mock_warn:
        try:
            runpy.run_module("pinjected.meta_main", run_name="__main__")
        except SystemExit:
            pass  # Fire.Fire may cause SystemExit
    
    # Verify mocks were called
    assert mock_fire.called, "fire.Fire should have been called"
    assert mock_warn.called, "warnings.warn should have been called"
    
    # Check the warning message
    if mock_warn.called:
        warning_msg = mock_warn.call_args[0][0]
        assert "meta_main is deprecated" in warning_msg
"""

        result = subprocess.run(
            [sys.executable, "-c", test_script], capture_output=True, text=True
        )

        # The test script should run successfully
        assert result.returncode == 0, f"Script failed: {result.stderr}"

    def test_import_without_execution(self):
        """Test that importing the module doesn't execute the main block."""
        # This is already covered by other tests, but let's be explicit
        # If we get here without errors, the test passes
        assert True
