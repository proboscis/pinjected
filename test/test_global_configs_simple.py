"""Simple tests for global_configs.py module."""

import pytest

from pinjected import global_configs


class TestGlobalConfigs:
    """Test the global_configs module."""

    def test_pinjected_track_origin_exists(self):
        """Test that pinjected_TRACK_ORIGIN variable exists."""
        assert hasattr(global_configs, "pinjected_TRACK_ORIGIN")

    def test_pinjected_track_origin_value(self):
        """Test the default value of pinjected_TRACK_ORIGIN."""
        assert global_configs.pinjected_TRACK_ORIGIN is True

    def test_pinjected_track_origin_type(self):
        """Test that pinjected_TRACK_ORIGIN is a boolean."""
        assert isinstance(global_configs.pinjected_TRACK_ORIGIN, bool)

    def test_module_contents(self):
        """Test that the module only contains expected attributes."""
        # Get all non-dunder attributes
        attrs = [attr for attr in dir(global_configs) if not attr.startswith("__")]

        # Should only have pinjected_TRACK_ORIGIN
        assert "pinjected_TRACK_ORIGIN" in attrs


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
