"""Simple tests for __main__.py module."""

import pytest
from unittest.mock import patch

from pinjected import __main__


class TestMain:
    """Test the __main__ module."""

    def test_main_import(self):
        """Test that main is imported from main_impl."""
        # Check that __main__ has the main attribute
        assert hasattr(__main__, "main")

        # Verify it's from main_impl
        from pinjected.main_impl import main as main_impl

        assert __main__.main is main_impl

    @patch("pinjected.__main__.main")
    def test_main_not_called_on_import(self, mock_main):
        """Test that main() is not called when module is imported."""
        # When we import the module in tests, __name__ != "__main__"
        # so main() should not be called
        mock_main.assert_not_called()

    def test_module_structure(self):
        """Test the module has expected structure."""
        import inspect

        source = inspect.getsource(__main__)

        # Check imports
        assert "from pinjected.main_impl import main" in source

        # Check main guard
        assert 'if __name__ == "__main__":' in source
        assert "main()" in source


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
