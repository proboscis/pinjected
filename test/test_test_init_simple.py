"""Simple tests for test/__init__.py module."""

import pytest


class TestTestInit:
    """Test the test package initialization."""

    def test_test_package_exports(self):
        """Test that the test package exports expected utilities."""
        from pinjected import test

        # Check __all__ exports
        assert hasattr(test, "__all__")
        assert "injected_pytest" in test.__all__
        assert "test_current_file" in test.__all__
        assert "test_tagged" in test.__all__
        assert "test_tree" in test.__all__

    def test_imported_functions(self):
        """Test that imported functions are available."""
        from pinjected import test

        # Check that the functions are available
        assert hasattr(test, "injected_pytest")
        assert hasattr(test, "test_current_file")
        assert hasattr(test, "test_tagged")
        assert hasattr(test, "test_tree")

    def test_module_docstring(self):
        """Test that the module has a Japanese docstring."""
        from pinjected import test

        assert test.__doc__ is not None
        # Contains Japanese text
        assert "テスト" in test.__doc__
        assert "ユーティリティ" in test.__doc__

    def test_direct_imports(self):
        """Test that we can import the exported functions directly."""
        # These imports should work
        from pinjected.test import injected_pytest
        from pinjected.test import test_current_file
        from pinjected.test import test_tagged
        from pinjected.test import test_tree

        # Verify they are imported
        assert injected_pytest is not None
        assert test_current_file is not None
        assert test_tagged is not None
        assert test_tree is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
