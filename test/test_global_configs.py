"""Tests for pinjected.global_configs module."""

import pytest
from unittest.mock import patch

from pinjected import global_configs


class TestGlobalConfigs:
    """Tests for global_configs module."""

    def test_pinjected_track_origin_exists(self):
        """Test that pinjected_TRACK_ORIGIN variable exists."""
        assert hasattr(global_configs, "pinjected_TRACK_ORIGIN")

    def test_pinjected_track_origin_default_value(self):
        """Test that pinjected_TRACK_ORIGIN has default value True."""
        assert global_configs.pinjected_TRACK_ORIGIN is True

    def test_pinjected_track_origin_is_bool(self):
        """Test that pinjected_TRACK_ORIGIN is a boolean."""
        assert isinstance(global_configs.pinjected_TRACK_ORIGIN, bool)

    def test_modify_pinjected_track_origin(self):
        """Test that pinjected_TRACK_ORIGIN can be modified."""
        original_value = global_configs.pinjected_TRACK_ORIGIN

        try:
            # Modify the value
            global_configs.pinjected_TRACK_ORIGIN = False
            assert global_configs.pinjected_TRACK_ORIGIN is False

            # Modify back to True
            global_configs.pinjected_TRACK_ORIGIN = True
            assert global_configs.pinjected_TRACK_ORIGIN is True
        finally:
            # Restore original value
            global_configs.pinjected_TRACK_ORIGIN = original_value

    @patch("pinjected.global_configs.pinjected_TRACK_ORIGIN", False)
    def test_patch_pinjected_track_origin(self):
        """Test patching pinjected_TRACK_ORIGIN in tests."""
        assert global_configs.pinjected_TRACK_ORIGIN is False

    def test_import_pinjected_track_origin(self):
        """Test importing pinjected_TRACK_ORIGIN directly."""
        from pinjected.global_configs import pinjected_TRACK_ORIGIN

        assert pinjected_TRACK_ORIGIN is True

    def test_global_configs_module_attributes(self):
        """Test global_configs module has expected attributes."""
        # Get all non-dunder attributes
        attrs = [attr for attr in dir(global_configs) if not attr.startswith("__")]

        # Should have at least pinjected_TRACK_ORIGIN
        assert "pinjected_TRACK_ORIGIN" in attrs

        # Check if there are any other configuration variables
        # This helps ensure we're testing all config variables
        config_attrs = [attr for attr in attrs if not attr.startswith("_")]
        assert len(config_attrs) >= 1  # At least pinjected_TRACK_ORIGIN


class TestGlobalConfigsUsage:
    """Tests demonstrating usage of global configs."""

    def test_conditional_based_on_track_origin(self):
        """Test using pinjected_TRACK_ORIGIN in conditional logic."""
        from pinjected.global_configs import pinjected_TRACK_ORIGIN

        def get_debug_info():
            if pinjected_TRACK_ORIGIN:
                return {"origin": "tracked", "debug": True}
            else:
                return {"origin": "not_tracked", "debug": False}

        # With default value (True)
        info = get_debug_info()
        assert info["origin"] == "tracked"
        assert info["debug"] is True

    def test_toggle_tracking_temporarily(self):
        """Test temporarily disabling origin tracking."""
        from pinjected import global_configs

        original = global_configs.pinjected_TRACK_ORIGIN
        results = []

        try:
            # Test with tracking enabled
            global_configs.pinjected_TRACK_ORIGIN = True
            results.append(("enabled", global_configs.pinjected_TRACK_ORIGIN))

            # Test with tracking disabled
            global_configs.pinjected_TRACK_ORIGIN = False
            results.append(("disabled", global_configs.pinjected_TRACK_ORIGIN))

        finally:
            global_configs.pinjected_TRACK_ORIGIN = original

        assert results[0] == ("enabled", True)
        assert results[1] == ("disabled", False)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
