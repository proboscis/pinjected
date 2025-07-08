"""Tests for pinjected.logging_helper module."""

import pytest
from unittest.mock import patch, call

from pinjected.logging_helper import disable_internal_logging


class TestDisableInternalLogging:
    """Test the disable_internal_logging context manager."""

    @patch("pinjected.logging_helper.logger")
    def test_disable_internal_logging_basic(self, mock_logger):
        """Test basic functionality of disable_internal_logging."""
        # Use the context manager
        with disable_internal_logging():
            pass

        # Check that disable was called for each module
        expected_names = [
            "pinjected.di.graph",
            "pinjected.helpers",
            "pinjected.module_inspector",
            "pinjected",
        ]

        # Check disable calls
        disable_calls = [call(name) for name in expected_names]
        mock_logger.disable.assert_has_calls(disable_calls, any_order=True)
        assert mock_logger.disable.call_count == len(expected_names)

        # Check enable calls
        enable_calls = [call(name) for name in expected_names]
        mock_logger.enable.assert_has_calls(enable_calls, any_order=True)
        assert mock_logger.enable.call_count == len(expected_names)

    @patch("pinjected.logging_helper.logger")
    def test_disable_internal_logging_order(self, mock_logger):
        """Test that disable happens before enable."""
        call_order = []

        mock_logger.disable.side_effect = lambda name: call_order.append(
            ("disable", name)
        )
        mock_logger.enable.side_effect = lambda name: call_order.append(
            ("enable", name)
        )

        with disable_internal_logging():
            # Check that all disables happened
            assert len([c for c in call_order if c[0] == "disable"]) == 4
            assert len([c for c in call_order if c[0] == "enable"]) == 0

        # After context, all enables should have happened
        assert len([c for c in call_order if c[0] == "enable"]) == 4

        # All disables should come before enables
        disable_indices = [
            i for i, (action, _) in enumerate(call_order) if action == "disable"
        ]
        enable_indices = [
            i for i, (action, _) in enumerate(call_order) if action == "enable"
        ]
        assert max(disable_indices) < min(enable_indices)

    @patch("pinjected.logging_helper.logger")
    def test_disable_internal_logging_with_exception(self, mock_logger):
        """Test behavior when exception occurs in context manager."""
        # Use the context manager with an exception
        with pytest.raises(ValueError), disable_internal_logging():
            raise ValueError("Test exception")

        # Check that disable was called
        expected_names = [
            "pinjected.di.graph",
            "pinjected.helpers",
            "pinjected.module_inspector",
            "pinjected",
        ]

        disable_calls = [call(name) for name in expected_names]
        mock_logger.disable.assert_has_calls(disable_calls, any_order=True)
        assert mock_logger.disable.call_count == len(expected_names)

        # Note: enable is NOT called when exception occurs because
        # the context manager doesn't use try/finally
        assert mock_logger.enable.call_count == 0

    @patch("pinjected.logging_helper.logger")
    def test_disable_internal_logging_yields(self, mock_logger):
        """Test that the context manager yields control."""
        yielded = False

        with disable_internal_logging():
            yielded = True

        assert yielded

    def test_module_imports(self):
        """Test module imports."""
        import pinjected.logging_helper

        assert hasattr(pinjected.logging_helper, "disable_internal_logging")
        assert callable(pinjected.logging_helper.disable_internal_logging)

    def test_imports_contextmanager(self):
        """Test that contextmanager is imported."""
        import pinjected.logging_helper
        import inspect

        source = inspect.getsource(pinjected.logging_helper)
        assert "from contextlib import contextmanager" in source

    def test_imports_logger(self):
        """Test that logger is imported."""
        import pinjected.logging_helper
        import inspect

        source = inspect.getsource(pinjected.logging_helper)
        assert "from pinjected.pinjected_logging import logger" in source

    @patch("pinjected.logging_helper.logger")
    def test_specific_module_names(self, mock_logger):
        """Test the specific module names being disabled."""
        with disable_internal_logging():
            pass

        # Get all module names that were disabled
        disabled_modules = [call[0][0] for call in mock_logger.disable.call_args_list]

        assert "pinjected.di.graph" in disabled_modules
        assert "pinjected.helpers" in disabled_modules
        assert "pinjected.module_inspector" in disabled_modules
        assert "pinjected" in disabled_modules


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
