"""Simple tests for notification.py module."""

import pytest
from unittest.mock import patch

from pinjected.notification import notify


class TestNotification:
    """Test the notification module."""

    @patch("platform.system")
    def test_notify_non_darwin_platform(self, mock_platform):
        """Test notify on non-macOS platform."""
        mock_platform.return_value = "Linux"

        result = notify("Test message")

        assert result == "Not supported on this platform (only macOS)"

    @patch("platform.system")
    @patch("os.system")
    def test_notify_darwin_platform(self, mock_os_system, mock_platform):
        """Test notify on macOS platform."""
        mock_platform.return_value = "Darwin"

        result = notify("Test message")

        # Check that os.system was called
        mock_os_system.assert_called_once()

        # Check the command format
        call_args = mock_os_system.call_args[0][0]
        assert "osascript" in call_args
        assert "display notification" in call_args
        assert "Test message" in call_args
        assert "OpenAI notification" in call_args
        assert "Glass" in call_args  # Default sound

        # Check return value
        assert result == "Notified user with text: Test message"

    @patch("platform.system")
    @patch("os.system")
    def test_notify_with_custom_sound(self, mock_os_system, mock_platform):
        """Test notify with custom sound."""
        mock_platform.return_value = "Darwin"

        result = notify("Test message", sound="Ping")

        # Check that the custom sound is used
        call_args = mock_os_system.call_args[0][0]
        assert "Ping" in call_args

        assert result == "Notified user with text: Test message"

    @patch("platform.system")
    @patch("os.system")
    def test_notify_escapes_quotes(self, mock_os_system, mock_platform):
        """Test notify escapes quotes in text."""
        mock_platform.return_value = "Darwin"

        result = notify("Test \"message\" with 'quotes'")

        # Check that quotes are removed from the command
        call_args = mock_os_system.call_args[0][0]
        assert '"' not in call_args.split("Test")[1].split("with")[0]
        assert "'" not in call_args.split("Test")[1].split("with")[0]

        # But the return value should have the original text
        assert result == "Notified user with text: Test \"message\" with 'quotes'"

    def test_notify_docstring(self):
        """Test that notify has proper docstring."""
        assert notify.__doc__ is not None
        assert "notification" in notify.__doc__
        assert "text" in notify.__doc__


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
