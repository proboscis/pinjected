"""Simple tests for meta_main.py module."""

import pytest

from pinjected import meta_main


class TestMetaMain:
    """Test the meta_main module functionality."""

    def test_module_imports(self):
        """Test that meta_main imports required modules."""
        # Check that the module has the expected imports
        import inspect

        source = inspect.getsource(meta_main)
        assert "import warnings" in source
        assert (
            "from pinjected.ide_supports.create_configs import run_with_meta_context"
            in source
        )
        assert "import fire" in source

    def test_main_execution(self):
        """Test the module has the expected structure."""
        # Verify run_with_meta_context is imported
        assert hasattr(meta_main, "run_with_meta_context")

        # Verify warnings module is imported
        assert hasattr(meta_main, "warnings")

    def test_deprecation_message(self):
        """Test the deprecation warning message."""
        # The deprecation message should be clear
        expected_message = "meta_main is deprecated and only maintained for backward compatibility with IDE plugins."

        # Check that this message is in the module
        import inspect

        source = inspect.getsource(meta_main)
        assert expected_message in source

    def test_module_docstring(self):
        """Test that the module has proper documentation."""
        # Check the module docstring content
        import inspect

        source = inspect.getsource(meta_main)

        # Check for key documentation elements
        assert "DEPRECATED:" in source
        assert "IDE plugins" in source
        assert "PyCharm, VSCode" in source
        assert "backward compatibility" in source


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
