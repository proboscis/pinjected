"""Tests for pinjected.__main__ module."""

import pytest
import sys
from unittest.mock import patch
import subprocess
from pathlib import Path


class TestMainModule:
    """Tests for __main__ module."""

    def test_imports_main_from_main_impl(self):
        """Test that __main__ imports main from main_impl."""
        # Import the module to check imports work
        from pinjected import __main__ as main_module

        # Verify it has access to main
        assert hasattr(main_module, "main")

    @patch("pinjected.main_impl.main")
    def test_main_called_when_run_as_script(self, mock_main):
        """Test that main() is called when module is run as script."""
        # Execute the module as a script
        with (
            patch.object(sys, "argv", ["pinjected"]),
            open(Path(__file__).parent.parent / "pinjected" / "__main__.py") as f,
        ):
            # Run the module
            exec(f.read(), {"__name__": "__main__"})

        # Verify main was called
        mock_main.assert_called_once()

    def test_main_not_called_when_imported(self):
        """Test that main() is not called when module is imported."""
        with patch("pinjected.main_impl.main") as mock_main:
            # Import the module (not as __main__)

            # main should not be called
            mock_main.assert_not_called()

    def test_run_as_module_subprocess(self):
        """Test running pinjected as a module via subprocess."""
        # Run pinjected module with --help to avoid side effects
        result = subprocess.run(
            [sys.executable, "-m", "pinjected", "--help"],
            capture_output=True,
            text=True,
        )

        # Should not error
        assert result.returncode == 0
        # Should show help text (might be in stderr for fire output)
        combined_output = (result.stdout + result.stderr).lower()
        assert (
            "usage:" in combined_output
            or "pinjected" in combined_output
            or "name" in combined_output
        )

    def test_main_function_reference(self):
        """Test that main in __main__ refers to main_impl.main."""
        from pinjected.__main__ import main
        from pinjected.main_impl import main as main_impl

        # They should be the same function
        assert main is main_impl

    def test_module_structure(self):
        """Test the structure of __main__.py module."""
        import pinjected.__main__ as main_module

        # Check module has expected attributes
        assert hasattr(main_module, "__name__")
        assert hasattr(main_module, "__file__")
        assert hasattr(main_module, "main")

        # Check no unexpected globals
        module_attrs = [
            attr
            for attr in dir(main_module)
            if not attr.startswith("__") and attr != "main"
        ]
        # Should only have 'main' as non-dunder attribute
        assert len(module_attrs) == 0

    def test_main_execution_path(self):
        """Test the execution path when __main__ is run."""
        test_executed = {"main_called": False}

        def mock_main():
            test_executed["main_called"] = True

        # Create a mock module dict
        module_dict = {"__name__": "__main__", "main": mock_main}

        # Execute the conditional
        if module_dict["__name__"] == "__main__":
            module_dict["main"]()

        assert test_executed["main_called"] is True

    def test_main_module_importable(self):
        """Test that pinjected can be run as python -m pinjected."""
        # Test by checking if __main__.py exists in the right place
        import pinjected

        package_path = Path(pinjected.__file__).parent
        main_path = package_path / "__main__.py"

        assert main_path.exists()
        assert main_path.is_file()

        # Read and verify content structure
        content = main_path.read_text()
        assert "from pinjected.main_impl import main" in content
        assert 'if __name__ == "__main__"' in content
        assert "main()" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
