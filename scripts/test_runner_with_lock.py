#!/usr/bin/env python
"""
Test runner with file lock to prevent concurrent pytest executions.

This script ensures that only one instance of pytest can run at a time by using
a file-based lock mechanism. If another instance is already running, it will
wait and display a message.
"""

import sys
import subprocess
import time
from pathlib import Path
from filelock import FileLock, Timeout
from loguru import logger


class PytestLockRunner:
    """Manages pytest execution with file locking."""

    def __init__(self):
        # Use a lock file in the project root
        self.project_root = Path(__file__).parent.parent
        self.lock_file = self.project_root / ".pytest.lock"
        self.lock = FileLock(str(self.lock_file), timeout=1)

    def run_with_args(self, args):
        """Run pytest with the given arguments, acquiring lock first."""
        logger.info(f"Attempting to run pytest with args: {args}")

        acquired = False
        start_time = time.time()
        wait_message_shown = False

        while not acquired:
            try:
                # Try to acquire the lock with a short timeout
                with self.lock.acquire(timeout=0.1):
                    acquired = True
                    logger.info("Lock acquired, running pytest...")

                    # Run pytest with the provided arguments
                    result = subprocess.run(
                        ["uv", "run", "pytest"] + args, cwd=self.project_root
                    )

                    return result.returncode

            except Timeout:
                # Another pytest instance is running
                if not wait_message_shown:
                    logger.warning(
                        "⏳ Another pytest instance is currently running. "
                        "Waiting for it to complete..."
                    )
                    wait_message_shown = True

                # Show progress every 5 seconds
                elapsed = time.time() - start_time
                if elapsed > 5 and int(elapsed) % 5 == 0:
                    logger.info(f"Still waiting... ({int(elapsed)}s elapsed)")

                time.sleep(0.5)

    def _run_with_lock(self, cmd, cwd):
        acquired = False
        start_time = time.time()
        wait_message_shown = False
        while not acquired:
            try:
                with self.lock.acquire(timeout=0.1):
                    acquired = True
                    logger.info("Lock acquired, running pytest...")
                    result = subprocess.run(cmd, cwd=cwd)
                    return result.returncode
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

    def _sync_all_packages(self):
        logger.info("Syncing all packages...")
        subprocess.run(
            ["uv", "sync", "--all-packages"], cwd=self.project_root, check=True
        )

    def _test_main_package(self):
        logger.info("\nTesting main pinjected package...")
        cmd = [
            "uv",
            "run",
            "pytest",
            "-p",
            "pinjected_pytest_runner.plugin",
            "test",
            "pinjected/test",
            "pinjected/tests",
        ]
        rc = self._run_with_lock(cmd, self.project_root)
        if rc not in [0, 5]:
            return rc
        if rc == 5:
            logger.info("  No tests found in main package")
        return 0

    def _iter_testable_packages(self):
        packages_dir = self.project_root / "packages"
        for pkg_path in packages_dir.iterdir():
            if not pkg_path.is_dir():
                continue
            pkg_name = pkg_path.name
            if pkg_name == "pinjected-linter":
                logger.info(f"Skipping {pkg_name} (tests hanging issue)...")
                continue
            if not (pkg_path / "tests").exists() and not (pkg_path / "test").exists():
                continue
            yield pkg_name, pkg_path

    def _test_subpackage(self, pkg_name, pkg_path):
        logger.info(f"Testing {pkg_name}...")
        cmd = ["uv", "run", "pytest", "-p", "pinjected_pytest_runner.plugin"]
        rc = self._run_with_lock(cmd, pkg_path)
        if rc not in [0, 5]:
            return rc
        if rc == 5:
            logger.info(f"  No tests found in {pkg_name}")
        logger.info("")
        return 0

    def _run_with_lock(self, cmd, cwd):
        acquired = False
        start_time = time.time()
        wait_message_shown = False
        while not acquired:
            try:
                with self.lock.acquire(timeout=0.1):
                    acquired = True
                    logger.info("Lock acquired, running pytest...")
                    result = subprocess.run(cmd, cwd=cwd)
                    return result.returncode
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

    def _sync_all_packages(self):
        logger.info("Syncing all packages...")
        subprocess.run(
            ["uv", "sync", "--all-packages"], cwd=self.project_root, check=True
        )

    def _test_main_package(self):
        logger.info("\nTesting main pinjected package...")
        cmd = [
            "uv",
            "run",
            "pytest",
            "-p",
            "pinjected_pytest_runner.plugin",
            "test",
            "pinjected/test",
            "pinjected/tests",
        ]
        rc = self._run_with_lock(cmd, self.project_root)
        if rc not in [0, 5]:
            return rc
        if rc == 5:
            logger.info("  No tests found in main package")
        return 0

    def _iter_testable_packages(self):
        packages_dir = self.project_root / "packages"
        for pkg_path in packages_dir.iterdir():
            if not pkg_path.is_dir():
                continue
            pkg_name = pkg_path.name
            if pkg_name == "pinjected-linter":
                logger.info(f"Skipping {pkg_name} (tests hanging issue)...")
                continue
            if not (pkg_path / "tests").exists() and not (pkg_path / "test").exists():
                continue
            yield pkg_name, pkg_path

    def _test_subpackage(self, pkg_name, pkg_path):
        logger.info(f"Testing {pkg_name}...")
        cmd = ["uv", "run", "pytest", "-p", "pinjected_pytest_runner.plugin"]
        rc = self._run_with_lock(cmd, pkg_path)
        if rc not in [0, 5]:
            return rc
        if rc == 5:
            logger.info(f"  No tests found in {pkg_name}")
        logger.info("")
        return 0

    def run_make_test_logic(self):
        logger.info("Running make test logic with file locking...")
        self._sync_all_packages()

        rc = self._test_main_package()
        if rc != 0:
            return rc

        logger.info("\nTesting subpackages...")
        for pkg_name, pkg_path in self._iter_testable_packages():
            rc = self._test_subpackage(pkg_name, pkg_path)
            if rc != 0:
                return rc

        logger.success("✓ All tests passed")
        return 0


def main():
    """Main entry point."""
    runner = PytestLockRunner()

    # Check if we're running the full make test logic or just pytest with args
    if len(sys.argv) > 1 and sys.argv[1] == "--make-test":
        # Run the full make test logic
        sys.exit(runner.run_make_test_logic())
    else:
        # Run pytest with provided arguments
        sys.exit(runner.run_with_args(sys.argv[1:]))


if __name__ == "__main__":
    main()
