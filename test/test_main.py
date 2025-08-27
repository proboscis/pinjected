"""Tests for __main__ module."""


class TestMain:
    """Test __main__ module."""

    def test_imports_main_from_main_impl(self):
        """Test that main is imported from main_impl."""
        # Import the module to check imports
        import pinjected.__main__ as main_module
        from pinjected.main_impl import main as expected_main

        # Check that main is available in the module
        assert hasattr(main_module, "main")
        assert main_module.main is expected_main

    def test_main_module_structure(self):
        """Test that the __main__ module has the expected structure."""
        # Read the actual module source code
        import pinjected.__main__
        import inspect

        source = inspect.getsource(pinjected.__main__)

        # Check that it imports main from main_impl
        assert "from pinjected.main_impl import main" in source

        # Check that it has the if __name__ == "__main__" guard
        assert 'if __name__ == "__main__":' in source
        assert "main()" in source

    def test_module_can_be_imported(self):
        """Test that the module can be imported without errors."""
        # This should not raise any exceptions
        import pinjected.__main__

        # Verify the module was imported
        assert pinjected.__main__ is not None

    def test_main_is_callable(self):
        """Test that main is a callable function."""
        import pinjected.__main__ as main_module

        # Check that main is callable
        assert callable(main_module.main)

    def test_module_structure(self):
        """Test the basic structure of the __main__ module."""
        import pinjected.__main__ as main_module

        # Check module has expected attributes
        assert hasattr(main_module, "__name__")
        assert hasattr(main_module, "__file__")
        assert hasattr(main_module, "main")
