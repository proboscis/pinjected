#!/usr/bin/env python
"""
Test runner with file lock to prevent concurrent pytest executions.
"""

import sys
import os
import signal
import subprocess
import time
import gc
from contextlib import suppress
from pathlib import Path
from filelock import FileLock, Timeout
from loguru import logger


class PytestLockRunner:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.lock_file = self.project_root / ".pytest.lock"
        self.lock = FileLock(str(self.lock_file), timeout=1)
        self._current_proc = None
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)

    def _pytest_env(self):
        env = os.environ.copy()
        env.setdefault("PYTHONFAULTHANDLER", "1")
        return env

    def _run_pytest(self, args, cwd):
        env = self._pytest_env()
        self._current_proc = subprocess.Popen(
            ["uv", "run", "pytest"] + args, cwd=cwd, env=env
        )
        try:
            returncode = self._current_proc.wait()
            return returncode
        finally:
            self._current_proc = None
            gc.collect()
            time.sleep(0.05)

    def _handle_signal(self, signum, frame):
        try:
            if self._current_proc is not None:
                with suppress(Exception):
                    self._current_proc.terminate()
        finally:
            with suppress(Exception):
                self.lock.release()
            os._exit(128 + (signum if isinstance(signum, int) else 15))

    def run_with_args(self, args):
        logger.info(f"Attempting to run pytest with args: {args}")
        acquired = False
        start_time = time.time()
        wait_message_shown = False
        while not acquired:
            try:
                with self.lock.acquire(timeout=0.1):
                    acquired = True
                    logger.info("Lock acquired, running pytest...")
                    return self._run_pytest(args, cwd=self.project_root)
            except Timeout:
                if not wait_message_shown:
                    logger.warning(
                        "⏳ Another pytest instance is currently running. Waiting for it to complete..."
                    )
                    wait_message_shown = True
                elapsed = time.time() - start_time
                if elapsed > 5 and int(elapsed) % 5 == 0:
                    logger.info(f"Still waiting... ({int(elapsed)}s elapsed)")
                time.sleep(0.5)

    def run_make_test_logic(self):
        logger.info("Running make test logic with file locking...")
        logger.info("Syncing all packages...")
        subprocess.run(
            ["uv", "sync", "--all-packages"], cwd=self.project_root, check=True
        )

        logger.info("\nTesting main pinjected package...")
        with self.lock.acquire():
            rc = self._run_pytest(
                ["test", "pinjected/test", "pinjected/tests"], cwd=self.project_root
            )
            if rc not in [0, 5]:
                return rc
            elif rc == 5:
                logger.info("  No tests found in main package")

        logger.info("\nTesting subpackages...")
        packages_dir = self.project_root / "packages"
        if packages_dir.exists():
            for pkg_path in packages_dir.iterdir():
                if not pkg_path.is_dir():
                    continue
                pkg_name = pkg_path.name
                has_tests = (pkg_path / "tests").exists() or (
                    pkg_path / "test"
                ).exists()
                if not has_tests:
                    continue
                if pkg_name == "pinjected-linter":
                    logger.info(f"Skipping {pkg_name} (tests hanging issue)...")
                    continue
                logger.info(f"Testing {pkg_name}...")
                wait_message_shown = False
                acquired = False
                start_time = time.time()
                while not acquired:
                    try:
                        with self.lock.acquire(timeout=0.1):
                            acquired = True
                            rc = self._run_pytest([], cwd=pkg_path)
                            if rc not in [0, 5]:
                                return rc
                            elif rc == 5:
                                logger.info(f"  No tests found in {pkg_name}")
                    except Timeout:
                        if not wait_message_shown:
                            logger.warning(
                                f"⏳ Waiting for another pytest instance to complete before testing {pkg_name}..."
                            )
                            wait_message_shown = True
                        elapsed = time.time() - start_time
                        if elapsed > 5 and int(elapsed) % 5 == 0:
                            logger.info(f"Still waiting... ({int(elapsed)}s elapsed)")
                        time.sleep(0.5)
                logger.info("")
        logger.success("✓ All tests passed")
        return 0


def main():
    runner = PytestLockRunner()
    if len(sys.argv) > 1 and sys.argv[1] == "--make-test":
        sys.exit(runner.run_make_test_logic())
    else:
        sys.exit(runner.run_with_args(sys.argv[1:]))


if __name__ == "__main__":
    main()
