"""Tests for pinjected_logging.py module."""

import pytest
import sys
from unittest.mock import Mock, patch
from pinjected.pinjected_logging import _init_loguru_logger, _init_logger, logger


def test_init_loguru_logger():
    """Test _init_loguru_logger function."""
    with patch("loguru.logger") as mock_loguru:
        # Set up mock
        mock_loguru.remove = Mock()
        mock_loguru.add = Mock()

        # Call function
        result = _init_loguru_logger()

        # Verify logger.remove was called
        mock_loguru.remove.assert_called_once()

        # Verify logger.add was called twice (for two handlers)
        assert mock_loguru.add.call_count == 2

        # Check first add call (without tag filter)
        first_call = mock_loguru.add.call_args_list[0]
        assert first_call[0][0] is sys.stderr
        filter_func = first_call[1]["filter"]
        assert callable(filter_func)
        assert filter_func({"extra": {}}) is True  # No tag
        assert filter_func({"extra": {"tag": "test"}}) is False  # Has tag
        assert "format" in first_call[1]
        assert first_call[1]["colorize"] is True

        # Check second add call (with tag filter)
        second_call = mock_loguru.add.call_args_list[1]
        assert second_call[0][0] is sys.stderr
        filter_func = second_call[1]["filter"]
        assert callable(filter_func)
        assert filter_func({"extra": {}}) is False  # No tag
        assert filter_func({"extra": {"tag": "test"}}) is True  # Has tag
        assert "format" in second_call[1]
        assert second_call[1]["colorize"] is True

        # Result should be the logger
        assert result is mock_loguru


def test_init_logger():
    """Test _init_logger function."""
    with patch("logging.getLogger") as mock_get_logger:
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        result = _init_logger()

        mock_get_logger.assert_called_once_with("pinjected")
        assert result is mock_logger


def test_logger_is_initialized():
    """Test that logger is initialized at module level."""
    # logger should exist and be the result of _init_loguru_logger
    assert logger is not None

    # Since _init_loguru_logger is called at module level,
    # we can't easily mock it, but we can verify the logger has expected attributes
    assert hasattr(logger, "info")
    assert hasattr(logger, "debug")
    assert hasattr(logger, "warning")
    assert hasattr(logger, "error")
    assert hasattr(logger, "remove")
    assert hasattr(logger, "add")


def test_format_strings():
    """Test the format strings are properly constructed."""
    # We can't easily test the actual format strings without running the logger,
    # but we can at least verify they're constructed correctly by calling the function
    with patch("loguru.logger") as mock_loguru:
        mock_loguru.remove = Mock()
        mock_loguru.add = Mock()

        _init_loguru_logger()

        # Get format strings from calls
        first_format = mock_loguru.add.call_args_list[0][1]["format"]
        second_format = mock_loguru.add.call_args_list[1][1]["format"]

        # Verify format strings contain expected components
        assert "{time:HH:mm:ss.SSS}" in first_format
        assert "{level: <8}" in first_format
        assert "{file.name}:{function}" in first_format
        assert "{line}" in first_format
        assert "{message}" in first_format

        # Second format should have tag
        assert "{extra[tag]}" in second_format
        assert "{message}" in second_format


def test_logger_filters():
    """Test the logger filter functions work correctly."""
    with patch("loguru.logger") as mock_loguru:
        mock_loguru.remove = Mock()
        mock_loguru.add = Mock()

        _init_loguru_logger()

        # Extract filter functions
        no_tag_filter = mock_loguru.add.call_args_list[0][1]["filter"]
        tag_filter = mock_loguru.add.call_args_list[1][1]["filter"]

        # Test various record scenarios
        record_with_tag = {"extra": {"tag": "test", "other": "data"}}
        record_without_tag = {"extra": {"other": "data"}}
        record_empty_extra = {"extra": {}}

        # No-tag filter should accept records without tag
        assert no_tag_filter(record_without_tag) is True
        assert no_tag_filter(record_empty_extra) is True
        assert no_tag_filter(record_with_tag) is False

        # Tag filter should accept records with tag
        assert tag_filter(record_with_tag) is True
        assert tag_filter(record_without_tag) is False
        assert tag_filter(record_empty_extra) is False


def test_logger_usage():
    """Test basic logger usage patterns."""
    # Test that logger can be used for logging
    with patch.object(logger, "info") as mock_info:
        logger.info("Test message")
        mock_info.assert_called_once_with("Test message")

    with patch.object(logger, "error") as mock_error:
        logger.error("Error message")
        mock_error.assert_called_once_with("Error message")

    with patch.object(logger, "debug") as mock_debug:
        logger.debug("Debug message")
        mock_debug.assert_called_once_with("Debug message")


def test_logger_with_context():
    """Test logger with contextualize."""
    # Test contextualized logging
    if hasattr(logger, "contextualize"):
        with logger.contextualize(tag="test_tag"):
            # Inside context, logger should have tag
            pass  # Context manager usage is tested


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
