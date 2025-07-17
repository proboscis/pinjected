"""Picklable wrapper for loguru logger."""

from typing import Any, Dict, Union, Optional, Callable, Tuple, TextIO, TYPE_CHECKING
from contextlib import contextmanager
from functools import wraps
from pathlib import Path
from loguru import logger as _loguru_logger

if TYPE_CHECKING:
    from logging import Handler


class PicklableLogger:
    """A picklable wrapper around loguru logger.

    This class provides the full loguru logger interface while being
    serializable with cloudpickle. It's designed to be used in pinjected
    designs where picklability is required.

    Note: Handler management (add/remove) and global configuration methods
    are delegated to the underlying loguru logger, as these typically
    shouldn't be serialized with the logger instance.
    """

    def __init__(self):
        """Initialize the logger with minimal configuration."""
        self._extra = {}
        self._disabled_modules = set()
        self._opt_defaults = {}

    def bind(self, **kwargs) -> "PicklableLogger":
        """Bind context variables to the logger."""
        new_logger = PicklableLogger()
        new_logger._extra = {**self._extra, **kwargs}
        new_logger._disabled_modules = self._disabled_modules.copy()
        new_logger._opt_defaults = self._opt_defaults.copy()
        return new_logger

    @contextmanager
    def contextualize(self, **kwargs):
        """Context manager to temporarily bind context variables."""
        with _loguru_logger.contextualize(**{**self._extra, **kwargs}):
            yield

    def opt(
        self,
        *,
        lazy: bool = False,
        colors: bool = False,
        raw: bool = False,
        capture: bool = True,
        depth: int = 0,
        exception: Optional[
            Union[bool, BaseException, Tuple[type, BaseException, Any]]
        ] = None,
        record: bool = False,
        **kwargs,
    ) -> "PicklableLogger":
        """Parametrize a logging call to slightly change generated log message.

        Args:
            lazy: Evaluate expensive functions only when needed
            colors: Enable colors in log message
            raw: Output raw message without formatting
            capture: Whether to capture kwargs into extra dict
            depth: Depth adjustment in the stack for finding caller
            exception: Display exception information
            record: Whether to format message with record values
            **kwargs: Additional options

        Returns:
            A new logger instance with specified options
        """
        new_logger = PicklableLogger()
        new_logger._extra = self._extra.copy()
        new_logger._disabled_modules = self._disabled_modules.copy()

        # Only store non-default values in opt_defaults
        opt_defaults = {}
        if lazy is not False:
            opt_defaults["lazy"] = lazy
        if colors is not False:
            opt_defaults["colors"] = colors
        if raw is not False:
            opt_defaults["raw"] = raw
        if capture is not True:
            opt_defaults["capture"] = capture
        if depth != 0:
            opt_defaults["depth"] = depth
        if exception is not None:
            opt_defaults["exception"] = exception
        if record is not False:
            opt_defaults["record"] = record
        opt_defaults.update(kwargs)

        new_logger._opt_defaults = opt_defaults
        return new_logger

    def _get_logger(self):
        """Get a logger with bound extras and options."""
        logger = _loguru_logger.bind(**self._extra) if self._extra else _loguru_logger
        if self._opt_defaults:
            logger = logger.opt(**self._opt_defaults)
        return logger

    # Logging methods
    def trace(self, message: str, *args, **kwargs):
        """Log a trace message."""
        return self._get_logger().trace(message, *args, **kwargs)

    def debug(self, message: str, *args, **kwargs):
        """Log a debug message."""
        return self._get_logger().debug(message, *args, **kwargs)

    def info(self, message: str, *args, **kwargs):
        """Log an info message."""
        return self._get_logger().info(message, *args, **kwargs)

    def success(self, message: str, *args, **kwargs):
        """Log a success message."""
        return self._get_logger().success(message, *args, **kwargs)

    def warning(self, message: str, *args, **kwargs):
        """Log a warning message."""
        return self._get_logger().warning(message, *args, **kwargs)

    def error(self, message: str, *args, **kwargs):
        """Log an error message."""
        return self._get_logger().error(message, *args, **kwargs)

    def critical(self, message: str, *args, **kwargs):
        """Log a critical message."""
        return self._get_logger().critical(message, *args, **kwargs)

    def exception(self, message: str, *args, **kwargs):
        """Log an exception with traceback."""
        return self._get_logger().exception(message, *args, **kwargs)

    def log(self, level: Union[str, int], message: str, *args, **kwargs):
        """Log a message with a specific level."""
        return self._get_logger().log(level, message, *args, **kwargs)

    # Handler management methods (delegate to global logger)
    def add(
        self,
        sink: Union[TextIO, str, Path, Callable, "Handler"],
        *,
        level: Union[str, int] = "DEBUG",
        format: Optional[Union[str, Callable]] = None,
        filter: Optional[Union[str, Dict, Callable]] = None,
        colorize: Optional[bool] = None,
        serialize: bool = False,
        backtrace: bool = True,
        diagnose: bool = True,
        enqueue: bool = False,
        catch: bool = True,
        **kwargs,
    ) -> int:
        """Add a handler to the logger.

        Note: This delegates to the global logger and the handler
        configuration is not preserved during pickling.
        """
        # Build kwargs dict to pass only non-None values
        add_kwargs = {
            "sink": sink,
            "level": level,
            "serialize": serialize,
            "backtrace": backtrace,
            "diagnose": diagnose,
            "enqueue": enqueue,
            "catch": catch,
        }

        if format is not None:
            add_kwargs["format"] = format
        if filter is not None:
            add_kwargs["filter"] = filter
        if colorize is not None:
            add_kwargs["colorize"] = colorize

        add_kwargs.update(kwargs)

        return _loguru_logger.add(**add_kwargs)

    def remove(self, handler_id: Optional[int] = None):
        """Remove a previously added handler."""
        return _loguru_logger.remove(handler_id)

    # Configuration methods
    def configure(
        self, *, handlers=None, levels=None, extra=None, patcher=None, activation=None
    ):
        """Configure the logger.

        Note: This affects the global logger configuration.
        """
        if extra is not None:
            # Merge with existing extra
            self._extra.update(extra)

        return _loguru_logger.configure(
            handlers=handlers,
            levels=levels,
            extra=extra,
            patcher=patcher,
            activation=activation,
        )

    def level(
        self,
        name: Union[str, int],
        no: Optional[int] = None,
        color: Optional[str] = None,
        icon: Optional[str] = None,
    ):
        """Add, update or retrieve a logging level."""
        return _loguru_logger.level(name, no=no, color=color, icon=icon)

    def disable(self, name: Optional[str] = None):
        """Disable logging for a specific module."""
        result = _loguru_logger.disable(name)
        if name:
            self._disabled_modules.add(name)
        return result

    def enable(self, name: Optional[str] = None):
        """Enable logging for a specific module."""
        result = _loguru_logger.enable(name)
        if name and name in self._disabled_modules:
            self._disabled_modules.remove(name)
        return result

    # Utility methods
    def catch(
        self,
        exception: Union[type, Tuple[type, ...]] = Exception,
        *,
        level: Union[str, int] = "ERROR",
        reraise: bool = False,
        onerror: Optional[Callable] = None,
        exclude: Optional[Union[type, Tuple[type, ...]]] = None,
        default: Optional[Any] = None,
        message: str = "An error has been caught in function '{record[function]}', process '{record[process].name}' ({record[process].id}), thread '{record[thread].name}' ({record[thread].id}):",
    ):
        """Decorator/context manager to catch and log exceptions."""

        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except exclude or ():
                    raise
                except exception as e:
                    self._get_logger().log(level, message)
                    if onerror:
                        onerror(e)
                    if reraise:
                        raise
                    return default

            return wrapper

        return decorator

    def patch(self, patcher: Callable[[Dict], None]):
        """Patch the log record dict."""
        return _loguru_logger.patch(patcher)

    def complete(self):
        """Wait for all handlers to process enqueued messages."""
        return _loguru_logger.complete()

    @staticmethod
    def parse(
        file: Union[str, Path, TextIO],
        pattern: str,
        *,
        cast: Optional[Dict[str, Callable]] = None,
        chunk: int = 2**16,
    ):
        """Parse a log file and yield records matching the pattern."""
        return _loguru_logger.parse(file, pattern, cast=cast, chunk=chunk)

    # Pickling support
    def __getstate__(self) -> Dict[str, Any]:
        """Get state for pickling."""
        return {
            "extra": self._extra,
            "disabled_modules": self._disabled_modules,
            "opt_defaults": self._opt_defaults,
        }

    def __setstate__(self, state: Dict[str, Any]):
        """Restore state after unpickling."""
        self._extra = state.get("extra", {})
        self._disabled_modules = state.get("disabled_modules", set())
        self._opt_defaults = state.get("opt_defaults", {})
