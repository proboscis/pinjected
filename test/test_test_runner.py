"""Comprehensive tests for pinjected/test_helper/test_runner.py module."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

from returns.result import Success, Failure

from pinjected.test_helper.test_runner import (
    PinjectedTestResult,
    escape_loguru_tags,
    CommandException,
    a_pinjected_run_test,
    a_pinjected_run_test__multiprocess,
    pinjected_test_aggregator,
    a_pinjected_run_all_test,
    ensure_agen,
    ITestEvent,
    MainTestEvent,
    StatusInfo,
    EventInfo,
    a_pinjected_test_event_callback__simple,
    a_pinjected_test_event_callback,
    a_run_tests,
    a_visualize_test_results,
    test_current_file,
    test_tagged,
    test_tree,
)
from pinjected.test_helper.test_aggregator import (
    VariableInFile,
    PinjectedTestAggregator,
)


class TestPinjectedTestResult:
    """Tests for PinjectedTestResult dataclass."""

    def test_pinjected_test_result_creation(self):
        """Test creating PinjectedTestResult."""
        target = Mock(spec=VariableInFile)
        target.to_module_var_path.return_value.path = "test.module.func"

        result = PinjectedTestResult(
            target=target,
            stdout="test output",
            stderr="test error",
            value=Success(0),
            trace=None,
        )

        assert result.target == target
        assert result.stdout == "test output"
        assert result.stderr == "test error"
        assert isinstance(result.value, Success)
        assert result.trace is None

    def test_pinjected_test_result_str(self):
        """Test string representation of PinjectedTestResult."""
        target = Mock(spec=VariableInFile)
        target.to_module_var_path.return_value.path = "test.module.func"

        result = PinjectedTestResult(
            target=target, stdout="", stderr="", value=Success(0), trace=None
        )

        assert str(result) == "PinjectedTestResult(test.module.func,<Success: 0>)"
        assert repr(result) == str(result)

    def test_pinjected_test_result_failed(self):
        """Test failed method."""
        target = Mock(spec=VariableInFile)

        # Success case
        result_success = PinjectedTestResult(
            target=target, stdout="", stderr="", value=Success(0), trace=None
        )
        assert not result_success.failed()

        # Failure case
        result_failure = PinjectedTestResult(
            target=target,
            stdout="",
            stderr="error",
            value=Failure(Exception("test error")),
            trace="stack trace",
        )
        assert result_failure.failed()


class TestEscapeLogutruTags:
    """Tests for escape_loguru_tags function."""

    def test_escape_loguru_tags_basic(self):
        """Test escaping loguru tags."""
        assert escape_loguru_tags("normal text") == "normal text"
        assert escape_loguru_tags("<tag>text</tag>") == r"\<tag>text\</tag>"
        assert escape_loguru_tags("<<multiple>>") == r"\<\<multiple>>"

    def test_escape_loguru_tags_empty(self):
        """Test escaping empty string."""
        assert escape_loguru_tags("") == ""


class TestCommandException:
    """Tests for CommandException class."""

    def test_command_exception_creation(self):
        """Test creating CommandException."""
        exc = CommandException(
            message="Command failed", code=1, stdout="output", stderr="error"
        )

        assert str(exc) == "Command failed"
        assert exc.message == "Command failed"
        assert exc.code == 1
        assert exc.stdout == "output"
        assert exc.stderr == "error"

    def test_command_exception_reduce(self):
        """Test pickling/unpickling CommandException."""
        exc = CommandException("test", 2, "out", "err")

        # Test __reduce__
        cls, args = exc.__reduce__()
        assert cls == CommandException
        assert args == ("test", 2, "out", "err")

        # Recreate from reduce
        exc2 = cls(*args)
        assert exc2.message == exc.message
        assert exc2.code == exc.code


class TestAPinjectedRunTest:
    """Tests for a_pinjected_run_test function."""

    @pytest.mark.asyncio
    @patch("asyncio.create_subprocess_shell")
    async def test_a_pinjected_run_test_success(self, mock_subprocess):
        """Test successful test run."""
        # Get the wrapped function
        if hasattr(a_pinjected_run_test, "__wrapped__"):
            func = a_pinjected_run_test.__wrapped__
        elif hasattr(a_pinjected_run_test, "src_function"):
            func = a_pinjected_run_test.src_function
        else:
            pytest.skip("Cannot access wrapped function")

        # Setup mocks
        logger = Mock()
        callback = AsyncMock()

        target = Mock(spec=VariableInFile)
        target.to_module_var_path.return_value.path = "test.module.func"

        # Mock subprocess
        proc = AsyncMock()
        proc.wait.return_value = 0
        proc.stdout.__aiter__.return_value = [b"output line\n"]
        proc.stderr.__aiter__.return_value = [b"error line\n"]
        mock_subprocess.return_value = proc

        # Run test with dependencies
        result = await func(logger, callback, target)

        # Verify result
        assert isinstance(result, PinjectedTestResult)
        assert result.target == target
        assert "output line" in result.stdout
        assert "error line" in result.stderr
        assert isinstance(result.value, Success)
        assert result.trace is None

        # Verify callbacks
        assert callback.call_count >= 2  # start and result

    @pytest.mark.asyncio
    @patch("asyncio.create_subprocess_shell")
    async def test_a_pinjected_run_test_failure(self, mock_subprocess):
        """Test failed test run."""
        # Get the wrapped function
        if hasattr(a_pinjected_run_test, "__wrapped__"):
            func = a_pinjected_run_test.__wrapped__
        elif hasattr(a_pinjected_run_test, "src_function"):
            func = a_pinjected_run_test.src_function
        else:
            pytest.skip("Cannot access wrapped function")

        logger = Mock()
        callback = AsyncMock()

        target = Mock(spec=VariableInFile)
        target.to_module_var_path.return_value.path = "test.module.func"

        # Mock subprocess with failure
        proc = AsyncMock()
        proc.wait.return_value = 1
        proc.stdout.__aiter__.return_value = []
        proc.stderr.__aiter__.return_value = [b"error message\n"]
        mock_subprocess.return_value = proc

        result = await func(logger, callback, target)

        assert result.failed()
        assert isinstance(result.value, Failure)
        assert isinstance(result.value.failure(), CommandException)
        assert result.trace is not None


class TestAPinjectedRunTestMultiprocess:
    """Tests for a_pinjected_run_test__multiprocess function."""

    @pytest.mark.asyncio
    @patch("pinjected.test_helper.test_runner.a_run_target__mp")
    async def test_multiprocess_success(self, mock_run_mp):
        """Test multiprocess test run success."""
        # Get the wrapped function
        if hasattr(a_pinjected_run_test__multiprocess, "__wrapped__"):
            func = a_pinjected_run_test__multiprocess.__wrapped__
        elif hasattr(a_pinjected_run_test__multiprocess, "src_function"):
            func = a_pinjected_run_test__multiprocess.src_function
        else:
            pytest.skip("Cannot access wrapped function")

        logger = Mock()
        target = Mock(spec=VariableInFile)
        target.to_module_var_path.return_value.path = "test.module.func"

        mock_run_mp.return_value = (
            "running target:test.module.func with design None\n",
            "stderr",
            None,
            "result",
        )

        result = await func(logger, target)

        assert isinstance(result, PinjectedTestResult)
        assert result.stdout == "running target:test.module.func with design None\n"
        assert result.stderr == "stderr"
        assert isinstance(result.value, Success)
        assert result.value.value_or(None) == "result"

    @pytest.mark.asyncio
    @patch("pinjected.test_helper.test_runner.a_run_target__mp")
    async def test_multiprocess_failure(self, mock_run_mp):
        """Test multiprocess test run with exception."""
        # Get the wrapped function
        if hasattr(a_pinjected_run_test__multiprocess, "__wrapped__"):
            func = a_pinjected_run_test__multiprocess.__wrapped__
        elif hasattr(a_pinjected_run_test__multiprocess, "src_function"):
            func = a_pinjected_run_test__multiprocess.src_function
        else:
            pytest.skip("Cannot access wrapped function")

        logger = Mock()
        target = Mock(spec=VariableInFile)
        target.to_module_var_path.return_value.path = "test.module.func"

        exc = Exception("test error")
        mock_run_mp.return_value = ("", "error", "trace", exc)

        result = await func(logger, target)

        assert result.failed()
        assert result.value.failure() == exc


class TestPinjectedTestAggregator:
    """Tests for pinjected_test_aggregator function."""

    def test_pinjected_test_aggregator(self):
        """Test creating test aggregator instance."""
        # pinjected_test_aggregator is decorated with @instance,
        # so we need to resolve it through the DI system
        from pinjected import design

        d = design()
        g = d.to_graph()
        result = g.provide(pinjected_test_aggregator)
        assert isinstance(result, PinjectedTestAggregator)


class TestAPinjectedRunAllTest:
    """Tests for a_pinjected_run_all_test function."""

    @pytest.mark.asyncio
    async def test_run_all_tests(self):
        """Test running all tests from aggregator."""
        # Get the wrapped function
        if hasattr(a_pinjected_run_all_test, "__wrapped__"):
            func = a_pinjected_run_all_test.__wrapped__
        elif hasattr(a_pinjected_run_all_test, "src_function"):
            func = a_pinjected_run_all_test.src_function
        else:
            pytest.skip("Cannot access wrapped function")

        # Setup mocks
        aggregator = Mock()
        target1 = Mock(spec=VariableInFile)
        target2 = Mock(spec=VariableInFile)
        aggregator.gather.return_value = [target1, target2]

        run_test = AsyncMock()
        result1 = Mock(spec=PinjectedTestResult)
        result2 = Mock(spec=PinjectedTestResult)
        run_test.side_effect = [result1, result2]

        logger = Mock()

        # Run all tests
        results = []
        async for result in func(aggregator, run_test, logger, Path("/test")):
            results.append(result)

        # Verify
        assert len(results) == 2
        assert result1 in results
        assert result2 in results
        aggregator.gather.assert_called_once_with(Path("/test"))


class TestEnsureAgen:
    """Tests for ensure_agen function."""

    @pytest.mark.asyncio
    async def test_ensure_agen_list(self):
        """Test converting list to async generator."""
        # Get the wrapped function
        if hasattr(ensure_agen, "__wrapped__"):
            func = ensure_agen.__wrapped__
        elif hasattr(ensure_agen, "src_function"):
            func = ensure_agen.src_function
        else:
            pytest.skip("Cannot access wrapped function")

        items = [1, 2, 3]

        result = func(items)
        collected = []
        async for item in result:
            collected.append(item)

        assert collected == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_ensure_agen_async_iterator(self):
        """Test passing through async iterator."""
        # Get the wrapped function
        if hasattr(ensure_agen, "__wrapped__"):
            func = ensure_agen.__wrapped__
        elif hasattr(ensure_agen, "src_function"):
            func = ensure_agen.src_function
        else:
            pytest.skip("Cannot access wrapped function")

        async def async_gen():
            yield 1
            yield 2
            yield 3

        result = func(async_gen())
        collected = []
        async for item in result:
            collected.append(item)

        assert collected == [1, 2, 3]


class TestTestEvents:
    """Tests for test event classes."""

    def test_test_main_event(self):
        """Test MainTestEvent creation."""
        event = MainTestEvent("start")
        assert event.kind == "start"
        assert isinstance(event, ITestEvent)

        event2 = MainTestEvent("end")
        assert event2.kind == "end"

    def test_test_status(self):
        """Test StatusInfo creation."""
        status = StatusInfo("Running test...")
        assert status.message == "Running test..."

    def test_test_event(self):
        """Test EventInfo creation."""
        # With literal status
        event1 = EventInfo("test.func", "queued")
        assert event1.name == "test.func"
        assert event1.data == "queued"

        # With result
        result = Mock(spec=PinjectedTestResult)
        event2 = EventInfo("test.func", result)
        assert event2.data == result

        # With StatusInfo
        status = StatusInfo("message")
        event3 = EventInfo("test.func", status)
        assert event3.data == status


class TestAPinjectedTestEventCallbackSimple:
    """Tests for a_pinjected_test_event_callback__simple function."""

    @pytest.mark.asyncio
    @patch("rich.print")
    async def test_callback_simple_success(self, mock_print):
        """Test simple callback with successful result."""
        # Get the wrapped function
        if hasattr(a_pinjected_test_event_callback__simple, "__wrapped__"):
            func = a_pinjected_test_event_callback__simple.__wrapped__
        elif hasattr(a_pinjected_test_event_callback__simple, "src_function"):
            func = a_pinjected_test_event_callback__simple.src_function
        else:
            pytest.skip("Cannot access wrapped function")

        logger = Mock()

        target = Mock(spec=VariableInFile)
        target.to_module_var_path.return_value.path = "test.func"
        target.file_path = "/test/file.py"
        target.name = "func"

        result = PinjectedTestResult(
            target=target, stdout="output", stderr="", value=Success(0), trace=None
        )

        event = EventInfo("test.func", result)

        await func(logger, event)

        # Should print success panel
        mock_print.assert_called_once()
        panel = mock_print.call_args[0][0]
        assert panel.title == "Success"
        assert "test.func" in panel.renderable

    @pytest.mark.asyncio
    @patch("rich.print")
    async def test_callback_simple_failure(self, mock_print):
        """Test simple callback with failed result."""
        # Get the wrapped function
        if hasattr(a_pinjected_test_event_callback__simple, "__wrapped__"):
            func = a_pinjected_test_event_callback__simple.__wrapped__
        elif hasattr(a_pinjected_test_event_callback__simple, "src_function"):
            func = a_pinjected_test_event_callback__simple.src_function
        else:
            pytest.skip("Cannot access wrapped function")

        logger = Mock()

        target = Mock(spec=VariableInFile)
        target.to_module_var_path.return_value.path = "test.func"
        target.file_path = "/test/file.py"
        target.name = "func"

        result = PinjectedTestResult(
            target=target,
            stdout="output",
            stderr="error",
            value=Failure(Exception("test")),
            trace="trace",
        )

        event = EventInfo("test.func", result)

        await func(logger, event)

        # Should print failure panel
        mock_print.assert_called_once()
        panel = mock_print.call_args[0][0]
        assert "Failed" in panel.title
        assert "error" in panel.renderable


class TestARunTests:
    """Tests for a_run_tests function."""

    @pytest.mark.asyncio
    @patch("multiprocessing.cpu_count")
    async def test_a_run_tests_basic(self, mock_cpu_count):
        """Test basic test running with worker pool."""
        # Get the wrapped function
        if hasattr(a_run_tests, "__wrapped__"):
            func = a_run_tests.__wrapped__
        elif hasattr(a_run_tests, "src_function"):
            func = a_run_tests.src_function
        else:
            pytest.skip("Cannot access wrapped function")

        mock_cpu_count.return_value = 2

        # Create test targets
        target1 = Mock(spec=VariableInFile)
        target1.to_module_var_path.return_value.path = "test1"
        target2 = Mock(spec=VariableInFile)
        target2.to_module_var_path.return_value.path = "test2"

        # Mock test runner
        result1 = Mock(spec=PinjectedTestResult)
        result2 = Mock(spec=PinjectedTestResult)
        run_test = AsyncMock(side_effect=[result1, result2])

        # Mock ensure_agen
        async def mock_agen(tests):
            for t in tests:
                yield t

        ensure_agen_mock = Mock(side_effect=mock_agen)

        # Mock callback
        callback = AsyncMock()

        # Run tests
        results = []
        async for result in func(
            run_test, ensure_agen_mock, callback, [target1, target2]
        ):
            results.append(result)

        # Verify
        assert len(results) == 2
        assert result1 in results
        assert result2 in results

        # Verify callbacks
        callback.assert_any_call(MainTestEvent("start"))
        callback.assert_any_call(MainTestEvent("end"))


class TestAVisualizeTestResults:
    """Tests for a_visualize_test_results function."""

    @pytest.mark.asyncio
    async def test_visualize_results(self):
        """Test visualizing test results."""
        # Get the wrapped function
        if hasattr(a_visualize_test_results, "__wrapped__"):
            func = a_visualize_test_results.__wrapped__
        elif hasattr(a_visualize_test_results, "src_function"):
            func = a_visualize_test_results.src_function
        else:
            pytest.skip("Cannot access wrapped function")

        logger = Mock()

        # Create test results
        result1 = Mock(spec=PinjectedTestResult)
        result1.failed.return_value = False
        result2 = Mock(spec=PinjectedTestResult)
        result2.failed.return_value = True

        # Mock ensure_agen
        async def mock_agen(tests):
            for t in tests:
                yield t

        ensure_agen_mock = Mock(side_effect=mock_agen)

        # Run visualization
        results = await func(logger, ensure_agen_mock, [result1, result2])

        # Verify
        assert len(results) == 2
        logger.info.assert_called_once()
        assert "1 / 2 failures" in logger.info.call_args[0][0]


class TestPublicInterfaces:
    """Tests for public interface functions."""

    @pytest.mark.skip(
        reason="Integration test exceeds 30s timeout and causes CI Error 137"
    )
    def test_test_current_file(self):
        """Test test_current_file function."""
        with patch("inspect.currentframe") as mock_frame:
            mock_frame.return_value.f_back.f_globals = {"__file__": "/test/file.py"}

            result = test_current_file()

            # Should return an injected function composition
            assert hasattr(result, "__call__")

    def test_test_tagged(self):
        """Test test_tagged function."""
        # Get the wrapped function
        if hasattr(test_tagged, "__wrapped__"):
            func = test_tagged.__wrapped__
        elif hasattr(test_tagged, "src_function"):
            func = test_tagged.src_function
        else:
            pytest.skip("Cannot access wrapped function")

        with pytest.raises(NotImplementedError):
            func("tag1", "tag2")

    @pytest.mark.skip(
        reason="Integration test exceeds 30s timeout and causes CI Error 137"
    )
    def test_test_tree(self):
        """Test test_tree function."""
        with patch("inspect.currentframe") as mock_frame:
            mock_frame.return_value.f_back.f_globals = {"__file__": "/test/file.py"}

            result = test_tree()

            # Should return an injected function composition
            assert hasattr(result, "__call__")


class TestIntegration:
    """Integration tests for test_runner module."""

    def test_module_constants(self):
        """Test module-level constants and configurations."""
        # Check that pinjected_run_tests_in_file is defined
        from pinjected.test_helper.test_runner import pinjected_run_tests_in_file

        assert hasattr(pinjected_run_tests_in_file, "__call__")

        # Check _run_test_in_file is defined
        from pinjected.test_helper.test_runner import _run_test_in_file

        assert hasattr(_run_test_in_file, "__call__")

    @pytest.mark.asyncio
    async def test_test_event_callback_factory(self):
        """Test the test event callback factory function."""
        # a_pinjected_test_event_callback is decorated with @instance,
        # so we need to resolve it through the DI system
        from pinjected import design
        from pinjected.v2.async_resolver import AsyncResolver
        from loguru import logger as real_logger

        d = design(logger=real_logger)

        # Use AsyncResolver since we're already in an async context
        resolver = AsyncResolver(d)

        # Get the callback function through DI
        # The resolver already executes the async function and returns the callback
        callback = await resolver.provide(a_pinjected_test_event_callback)

        # Should return a callable
        assert callable(callback)

        # Test with start event
        await callback(EventInfo("test", "start"))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
