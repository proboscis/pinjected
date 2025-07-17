"""Tests for PicklableLogger to ensure it covers all loguru logger methods."""

import pickle
import tempfile
from pathlib import Path
from io import StringIO

from pinjected.picklable_logger import PicklableLogger


class TestPicklableLoggerMethods:
    """Test all public methods of PicklableLogger match loguru's API."""

    def test_logging_methods(self):
        """Test all standard logging methods exist and work."""
        logger = PicklableLogger()

        # Test all logging levels
        logger.trace("Trace message")
        logger.debug("Debug message")
        logger.info("Info message")
        logger.success("Success message")
        logger.warning("Warning message")
        logger.error("Error message")
        logger.critical("Critical message")

        # Test log with custom level
        logger.log("INFO", "Custom level message")

        # Test exception (without actual exception)
        logger.exception("Exception message")

    def test_bind_method(self):
        """Test bind creates new logger with context."""
        logger = PicklableLogger()
        bound_logger = logger.bind(user="test_user", request_id=123)

        assert isinstance(bound_logger, PicklableLogger)
        assert bound_logger._extra == {"user": "test_user", "request_id": 123}
        assert logger._extra == {}  # Original unchanged

        # Test chaining
        double_bound = bound_logger.bind(extra="data")
        assert double_bound._extra == {
            "user": "test_user",
            "request_id": 123,
            "extra": "data",
        }

    def test_contextualize_method(self):
        """Test contextualize context manager."""
        logger = PicklableLogger()

        with logger.contextualize(request_id=456):
            logger.info("Inside context")

        # Context should be cleared after
        logger.info("Outside context")

    def test_opt_method(self):
        """Test opt method for parametrizing logging."""
        logger = PicklableLogger()

        # Test various opt parameters
        opt_logger = logger.opt(
            lazy=True,
            colors=True,
            raw=False,
            capture=False,
            depth=2,
            exception=True,
            record=True,
        )

        assert isinstance(opt_logger, PicklableLogger)
        assert opt_logger._opt_defaults["lazy"] is True
        assert opt_logger._opt_defaults["colors"] is True
        assert opt_logger._opt_defaults["depth"] == 2

    def test_add_remove_handlers(self):
        """Test add and remove handler methods."""
        logger = PicklableLogger()

        # Test adding handler
        handler_id = logger.add(
            StringIO(),
            level="DEBUG",
            format="{time} {level} {message}",
            filter=lambda record: True,
            colorize=False,
            serialize=False,
            backtrace=True,
            diagnose=True,
            enqueue=False,
            catch=True,
        )

        assert isinstance(handler_id, int)

        # Test removing handler
        logger.remove(handler_id)
        logger.remove()  # Remove all

    def test_configuration_methods(self):
        """Test configure and level methods."""
        logger = PicklableLogger()

        # Test configure
        logger.configure(
            handlers=[], levels=[], extra={"app": "test"}, patcher=None, activation=[]
        )

        # Test level
        logger.level("CUSTOM", no=25, color="<red>", icon="🔧")
        result = logger.level("INFO")
        assert result is not None

    def test_enable_disable_methods(self):
        """Test enable/disable logging for modules."""
        logger = PicklableLogger()

        # Test disable
        logger.disable("some.module")
        assert "some.module" in logger._disabled_modules

        # Test enable
        logger.enable("some.module")
        assert "some.module" not in logger._disabled_modules

        # Test global disable/enable
        logger.disable()
        logger.enable()

    def test_catch_decorator(self):
        """Test catch decorator/context manager."""
        logger = PicklableLogger()

        @logger.catch()
        def may_fail():
            return 1 / 1

        result = may_fail()
        assert result == 1

        @logger.catch(ValueError, reraise=False, default=0)
        def will_fail():
            raise ValueError("Test error")

        result = will_fail()
        assert result == 0

    def test_utility_methods(self):
        """Test patch, complete, and parse methods."""
        logger = PicklableLogger()

        # Test patch
        def patcher(record):
            record["extra_field"] = "patched"

        logger.patch(patcher)

        # Test complete
        logger.complete()

        # Test parse (static method)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as f:
            f.write("2023-01-01 00:00:00 | INFO | Test message\n")
            f.flush()

            results = list(
                PicklableLogger.parse(
                    f.name,
                    pattern=r"(?P<time>.*?) \| (?P<level>\w+) \| (?P<message>.*)",
                    cast={"time": str, "level": str, "message": str},
                )
            )

            assert len(results) > 0

        Path(f.name).unlink()

    def test_pickling(self):
        """Test that PicklableLogger can be pickled and unpickled."""
        logger = PicklableLogger()
        logger = logger.bind(user="test", session=123)
        logger.disable("test.module")
        logger = logger.opt(lazy=True, depth=2)

        # Pickle and unpickle
        pickled = pickle.dumps(logger)
        restored = pickle.loads(pickled)

        # Verify state is preserved
        assert restored._extra == {"user": "test", "session": 123}
        assert "test.module" in restored._disabled_modules
        assert restored._opt_defaults["lazy"] is True
        assert restored._opt_defaults["depth"] == 2

        # Verify restored logger works
        restored.info("Restored logger works!")

    def test_all_methods_present(self):
        """Verify all expected loguru methods are present."""
        logger = PicklableLogger()

        # List of all public methods that should be present
        expected_methods = [
            # Logging methods
            "trace",
            "debug",
            "info",
            "success",
            "warning",
            "error",
            "critical",
            "exception",
            "log",
            # Configuration
            "bind",
            "contextualize",
            "opt",
            "add",
            "remove",
            "configure",
            "level",
            "enable",
            "disable",
            # Utilities
            "catch",
            "patch",
            "complete",
            "parse",
        ]

        for method_name in expected_methods:
            assert hasattr(logger, method_name), f"Missing method: {method_name}"
            assert callable(getattr(logger, method_name)), (
                f"Not callable: {method_name}"
            )


class TestPicklableLoggerBehavior:
    """Test specific behaviors of PicklableLogger."""

    def test_bind_preserves_state(self):
        """Test that bind preserves all internal state."""
        logger = PicklableLogger()
        logger.disable("module1")
        logger = logger.opt(depth=3)

        bound = logger.bind(key="value")

        # All state should be preserved
        assert "module1" in bound._disabled_modules
        assert bound._opt_defaults["depth"] == 3
        assert bound._extra == {"key": "value"}

    def test_opt_creates_new_instance(self):
        """Test that opt creates a new instance."""
        logger = PicklableLogger()
        opt_logger = logger.opt(lazy=True)

        assert logger is not opt_logger
        assert logger._opt_defaults == {}
        assert opt_logger._opt_defaults == {"lazy": True}

    def test_handler_methods_delegate_to_global(self):
        """Test that handler methods work with global logger."""
        logger = PicklableLogger()

        # Should not raise
        handler_id = logger.add(StringIO())
        logger.remove(handler_id)
