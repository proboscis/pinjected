"""Simple tests for __main__.py module."""

import pytest
from unittest.mock import patch
import sys


class TestMain:
    """Test the __main__ module."""

    def test_main_module_imports(self):
        """Test that __main__ module can be imported."""
        # Import the module to ensure it exists
        import pinjected.__main__

        assert pinjected.__main__ is not None

    @patch("pinjected.main_impl.main")
    def test_main_called_when_run_as_script(self, mock_main):
        """Test that main() is called when module is run as script."""
        # Save original argv
        original_argv = sys.argv[:]

        try:
            # Set up test argv
            sys.argv = ["pinjected"]

            # Execute the module as a script
            import pinjected.__main__

            # Since __main__.py has if __name__ == "__main__", we need to
            # simulate running it directly
            with (
                patch("pinjected.__main__.__name__", "__main__"),
                open(pinjected.__main__.__file__) as f,
            ):
                # Re-execute the module code
                exec(f.read(), {"__name__": "__main__"})

            # Verify main was called
            mock_main.assert_called_once()

        finally:
            # Restore original argv
            sys.argv = original_argv

    def test_main_function_exists(self):
        """Test that main function exists in main_impl."""
        from pinjected.main_impl import main

        assert callable(main)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
