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

    def run_make_test_logic(self):
        """Execute the make test logic with locking for each pytest invocation."""
        logger.info("Running make test logic with file locking...")

        # Sync all packages first
        logger.info("Syncing all packages...")
        subprocess.run(
            ["uv", "sync", "--all-packages"], cwd=self.project_root, check=True
        )

        # Test main pinjected package
        logger.info("\nTesting main pinjected package...")
        with self.lock.acquire():
            result = subprocess.run(
                ["uv", "run", "pytest", "test", "pinjected/test", "pinjected/tests"],
                cwd=self.project_root,
            )
            if result.returncode not in [0, 5]:  # 5 = no tests found
                return result.returncode
            elif result.returncode == 5:
                logger.info("  No tests found in main package")

        # Test subpackages
        logger.info("\nTesting subpackages...")
        packages_dir = self.project_root / "packages"

        for pkg_path in packages_dir.iterdir():
            if not pkg_path.is_dir():
                continue

            pkg_name = pkg_path.name

            # Check if package has tests
            has_tests = (pkg_path / "tests").exists() or (pkg_path / "test").exists()
            if not has_tests:
                continue

            # Skip pinjected-linter as noted in Makefile
            if pkg_name == "pinjected-linter":
                logger.info(f"Skipping {pkg_name} (tests hanging issue)...")
                continue

            logger.info(f"Testing {pkg_name}...")

            # Acquire lock for each package test
            wait_message_shown = False
            acquired = False
            start_time = time.time()

            while not acquired:
                try:
                    with self.lock.acquire(timeout=0.1):
                        acquired = True
                        result = subprocess.run(["uv", "run", "pytest"], cwd=pkg_path)
                        if result.returncode not in [0, 5]:
                            return result.returncode
                        elif result.returncode == 5:
                            logger.info(f"  No tests found in {pkg_name}")

                except Timeout:
                    if not wait_message_shown:
                        logger.warning(
                            f"⏳ Waiting for another pytest instance to complete "
                            f"before testing {pkg_name}..."
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
