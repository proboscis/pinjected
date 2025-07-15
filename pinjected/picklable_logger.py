"""Picklable wrapper for loguru logger."""

from typing import Any, Dict, Union
from contextlib import contextmanager
from loguru import logger as _loguru_logger


class PicklableLogger:
    """A picklable wrapper around loguru logger.

    This class provides a subset of the loguru logger interface while being
    serializable with cloudpickle. It's designed to be used in pinjected
    designs where picklability is required.
    """

    def __init__(self):
        """Initialize the logger with minimal configuration."""
        self._extra = {}

    def bind(self, **kwargs) -> "PicklableLogger":
        """Bind context variables to the logger."""
        new_logger = PicklableLogger()
        new_logger._extra = {**self._extra, **kwargs}
        return new_logger

    @contextmanager
    def contextualize(self, **kwargs):
        """Context manager to temporarily bind context variables."""
        with _loguru_logger.contextualize(**{**self._extra, **kwargs}):
            yield

    # Logging methods
    def trace(self, message: str, *args, **kwargs):
        """Log a trace message."""
        bound_logger = (
            _loguru_logger.bind(**self._extra) if self._extra else _loguru_logger
        )
        return bound_logger.trace(message, *args, **kwargs)

    def debug(self, message: str, *args, **kwargs):
        """Log a debug message."""
        bound_logger = (
            _loguru_logger.bind(**self._extra) if self._extra else _loguru_logger
        )
        return bound_logger.debug(message, *args, **kwargs)

    def info(self, message: str, *args, **kwargs):
        """Log an info message."""
        bound_logger = (
            _loguru_logger.bind(**self._extra) if self._extra else _loguru_logger
        )
        return bound_logger.info(message, *args, **kwargs)

    def success(self, message: str, *args, **kwargs):
        """Log a success message."""
        bound_logger = (
            _loguru_logger.bind(**self._extra) if self._extra else _loguru_logger
        )
        return bound_logger.success(message, *args, **kwargs)

    def warning(self, message: str, *args, **kwargs):
        """Log a warning message."""
        bound_logger = (
            _loguru_logger.bind(**self._extra) if self._extra else _loguru_logger
        )
        return bound_logger.warning(message, *args, **kwargs)

    def error(self, message: str, *args, **kwargs):
        """Log an error message."""
        bound_logger = (
            _loguru_logger.bind(**self._extra) if self._extra else _loguru_logger
        )
        return bound_logger.error(message, *args, **kwargs)

    def critical(self, message: str, *args, **kwargs):
        """Log a critical message."""
        bound_logger = (
            _loguru_logger.bind(**self._extra) if self._extra else _loguru_logger
        )
        return bound_logger.critical(message, *args, **kwargs)

    def exception(self, message: str, *args, **kwargs):
        """Log an exception with traceback."""
        bound_logger = (
            _loguru_logger.bind(**self._extra) if self._extra else _loguru_logger
        )
        return bound_logger.exception(message, *args, **kwargs)

    def log(self, level: Union[str, int], message: str, *args, **kwargs):
        """Log a message with a specific level."""
        bound_logger = (
            _loguru_logger.bind(**self._extra) if self._extra else _loguru_logger
        )
        return bound_logger.log(level, message, *args, **kwargs)

    # Pickling support
    def __getstate__(self) -> Dict[str, Any]:
        """Get state for pickling."""
        return {"extra": self._extra}

    def __setstate__(self, state: Dict[str, Any]):
        """Restore state after unpickling."""
        self._extra = state.get("extra", {})
