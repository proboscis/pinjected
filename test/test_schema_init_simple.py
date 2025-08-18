"""Simple tests for schema/__init__.py module."""

import pytest


class TestSchemaInit:
    """Test the schema package initialization."""

    def test_schema_package_exists(self):
        """Test that the schema package can be imported."""
        import pinjected.schema

        assert pinjected.schema is not None

    def test_schema_module_path(self):
        """Test that the schema module has correct path."""
        import pinjected.schema

        assert hasattr(pinjected.schema, "__file__")
        assert "schema/__init__.py" in pinjected.schema.__file__

    def test_schema_is_package(self):
        """Test that schema is a package."""
        import pinjected.schema

        assert hasattr(pinjected.schema, "__path__")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
