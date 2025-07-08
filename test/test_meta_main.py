"""Tests for pinjected.meta_main module."""

import pytest
from unittest.mock import patch


class TestMetaMain:
    """Test the meta_main module."""

    def test_imports(self):
        """Test that module can be imported."""
        import pinjected.meta_main

        assert pinjected.meta_main is not None

    def test_has_run_with_meta_context_import(self):
        """Test that run_with_meta_context is imported."""
        from pinjected.meta_main import run_with_meta_context

        assert run_with_meta_context is not None

    @patch("fire.Fire")
    @patch("pinjected.meta_main.warnings.warn")
    def test_main_execution(self, mock_warn, mock_fire):
        """Test execution when run as main."""
        # Import the module
        import pinjected.meta_main

        # Simulate running as __main__
        with (
            patch.object(pinjected.meta_main, "__name__", "__main__"),
            open(pinjected.meta_main.__file__) as f,
        ):
            # Re-execute the module
            exec(f.read(), {"__name__": "__main__"})

        # Check warnings.warn was called with deprecation message
        mock_warn.assert_called_once()
        args = mock_warn.call_args[0]
        assert "meta_main is deprecated" in args[0]
        assert args[1] is DeprecationWarning

        # Check fire.Fire was called with run_with_meta_context
        mock_fire.assert_called_once()
        from pinjected.ide_supports.create_configs import run_with_meta_context

        mock_fire.assert_called_with(run_with_meta_context)

    def test_module_docstring(self):
        """Test the __main__ block has a docstring."""
        import pinjected.meta_main

        # Read the source to check for docstring
        with open(pinjected.meta_main.__file__, "r") as f:
            content = f.read()

        assert '"""' in content
        assert (
            "An entrypoint for running a injected with __design__ integrated."
            in content
        )
        assert "DEPRECATED" in content

    def test_warnings_import(self):
        """Test that warnings module is imported."""
        import pinjected.meta_main
        import inspect

        # Get module members
        members = inspect.getmembers(pinjected.meta_main)
        module_dict = dict(members)

        # Check warnings is available
        assert "warnings" in module_dict or hasattr(pinjected.meta_main, "warnings")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
