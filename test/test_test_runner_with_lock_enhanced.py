import signal
from unittest import mock


from scripts.test_runner_with_lock import PytestLockRunner


def test_run_with_args_invokes_pytest_with_env(monkeypatch):
    runner = PytestLockRunner()

    mocked_proc = mock.Mock()
    mocked_proc.wait.return_value = 0

    def popen_side_effect(cmd, cwd=None, env=None):
        assert cmd[:3] == ["uv", "run", "pytest"]
        assert isinstance(env, dict)
        assert env.get("PYTHONFAULTHANDLER") == "1"
        assert cwd == runner.project_root
        return mocked_proc

    with mock.patch("subprocess.Popen", side_effect=popen_side_effect):
        rc = runner.run_with_args([])
        assert rc == 0
        mocked_proc.wait.assert_called_once()


def test_signal_handler_terminates_child(monkeypatch):
    runner = PytestLockRunner()
    mocked_proc = mock.Mock()
    runner._current_proc = mocked_proc

    with mock.patch("os._exit") as mock_exit:
        runner._handle_signal(signal.SIGTERM, None)
        mocked_proc.terminate.assert_called_once()
        mock_exit.assert_called_once()
        args, kwargs = mock_exit.call_args
        assert args and isinstance(args[0], int)


def test_make_test_logic_handles_no_tests(monkeypatch, tmp_path):
    runner = PytestLockRunner()

    def sync_side_effect(cmd, cwd=None, check=None):
        assert cmd == ["uv", "sync", "--all-packages"]
        return mock.Mock()

    mocked_proc = mock.Mock()
    mocked_proc.wait.return_value = 5

    with (
        mock.patch("subprocess.run", side_effect=sync_side_effect),
        mock.patch("subprocess.Popen", return_value=mocked_proc),
    ):
        rc = runner.run_make_test_logic()
        assert rc == 0
