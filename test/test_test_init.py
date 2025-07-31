"""Tests for pinjected.test.__init__ module."""

import pytest


class TestTestInit:
    """Test the test package initialization."""

    def test_imports(self):
        """Test that all expected imports work."""
        from pinjected.test import (
            injected_pytest,
            test_current_file,
            test_tagged,
            test_tree,
        )

        # Verify they are callable or importable
        assert injected_pytest is not None
        assert callable(test_current_file)
        assert callable(test_tagged)
        assert callable(test_tree)

    def test_all_exports(self):
        """Test that __all__ contains expected exports."""
        import pinjected.test

        assert hasattr(pinjected.test, "__all__")
        expected = ["injected_pytest", "test_current_file", "test_tagged", "test_tree"]
        assert set(pinjected.test.__all__) == set(expected)

    def test_module_docstring(self):
        """Test that module has a docstring."""
        import pinjected.test

        assert pinjected.test.__doc__ is not None
        # Check for Japanese text or just check it has content
        assert len(pinjected.test.__doc__) > 0

    def test_individual_imports(self):
        """Test importing items individually."""
        from pinjected.test import injected_pytest
        from pinjected.test import test_current_file
        from pinjected.test import test_tagged
        from pinjected.test import test_tree

        # Just verify imports succeed
        assert injected_pytest is not None
        assert test_current_file is not None
        assert test_tagged is not None
        assert test_tree is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
