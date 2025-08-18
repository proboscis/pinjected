"""Tests for pinjected.global_configs module."""

import pytest


class TestGlobalConfigs:
    """Test the global_configs module."""

    def test_pinjected_track_origin_exists(self):
        """Test that pinjected_TRACK_ORIGIN variable exists."""
        from pinjected.global_configs import pinjected_TRACK_ORIGIN

        assert pinjected_TRACK_ORIGIN is not None

    def test_pinjected_track_origin_is_bool(self):
        """Test that pinjected_TRACK_ORIGIN is a boolean."""
        from pinjected.global_configs import pinjected_TRACK_ORIGIN

        assert isinstance(pinjected_TRACK_ORIGIN, bool)

    def test_pinjected_track_origin_default_value(self):
        """Test the default value of pinjected_TRACK_ORIGIN."""
        from pinjected.global_configs import pinjected_TRACK_ORIGIN

        assert pinjected_TRACK_ORIGIN is True

    def test_module_imports(self):
        """Test that module can be imported."""
        import pinjected.global_configs

        assert pinjected.global_configs is not None

    def test_module_attributes(self):
        """Test module attributes."""
        import pinjected.global_configs

        assert hasattr(pinjected.global_configs, "pinjected_TRACK_ORIGIN")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
