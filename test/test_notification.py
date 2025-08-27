"""Tests for notification.py module."""

import pytest
from unittest.mock import patch
from pinjected.notification import notify


@patch("platform.system")
def test_notify_non_darwin_platform(mock_platform):
    """Test notify on non-macOS platform."""
    mock_platform.return_value = "Linux"

    result = notify("Test message")

    assert result == "Not supported on this platform (only macOS)"


@patch("platform.system")
@patch("os.system")
def test_notify_on_darwin(mock_system, mock_platform):
    """Test notify on macOS platform."""
    mock_platform.return_value = "Darwin"

    result = notify("Test notification")

    # Check that os.system was called with osascript command
    mock_system.assert_called_once()
    call_args = mock_system.call_args[0][0]
    assert "osascript -e" in call_args
    assert "Test notification" in call_args
    assert "OpenAI notification" in call_args
    assert "Glass" in call_args  # Default sound

    assert result == "Notified user with text: Test notification"


@patch("platform.system")
@patch("os.system")
def test_notify_with_custom_sound(mock_system, mock_platform):
    """Test notify with custom sound."""
    mock_platform.return_value = "Darwin"

    result = notify("Alert!", sound="Ping")

    # Check that custom sound is used
    call_args = mock_system.call_args[0][0]
    assert "Ping" in call_args
    assert result == "Notified user with text: Alert!"


@patch("platform.system")
@patch("os.system")
def test_notify_escapes_quotes(mock_system, mock_platform):
    """Test notify properly escapes quotes in text."""
    mock_platform.return_value = "Darwin"

    # Test with double quotes
    result = notify('Text with "quotes"')
    call_args = mock_system.call_args[0][0]
    assert "Text with quotes" in call_args  # Quotes should be removed
    assert result == 'Notified user with text: Text with "quotes"'

    # Test with single quotes
    mock_system.reset_mock()
    result = notify("Text with 'quotes'")
    call_args = mock_system.call_args[0][0]
    assert "Text with quotes" in call_args  # Quotes should be removed
    assert result == "Notified user with text: Text with 'quotes'"


@patch("platform.system")
@patch("os.system")
def test_notify_with_mixed_quotes(mock_system, mock_platform):
    """Test notify with both single and double quotes."""
    mock_platform.return_value = "Darwin"

    result = notify("""Text with "double" and 'single' quotes""")

    call_args = mock_system.call_args[0][0]
    assert "Text with double and single quotes" in call_args
    assert (
        result == """Notified user with text: Text with "double" and 'single' quotes"""
    )


@patch("platform.system")
@patch("os.system")
def test_notify_command_format(mock_system, mock_platform):
    """Test the exact osascript command format."""
    mock_platform.return_value = "Darwin"

    notify("Hello World", sound="Pop")

    expected_script = '\'display notification "Hello World" with title "OpenAI notification" sound name "Pop"\''
    expected_cmd = f"osascript -e {expected_script} "

    mock_system.assert_called_once_with(expected_cmd)


@patch("platform.system")
def test_notify_windows_platform(mock_platform):
    """Test notify on Windows platform."""
    mock_platform.return_value = "Windows"

    result = notify("Windows notification")

    assert result == "Not supported on this platform (only macOS)"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
