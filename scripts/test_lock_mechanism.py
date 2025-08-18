#!/usr/bin/env python
"""Test the pytest lock mechanism by simulating concurrent test runs."""

import subprocess
import threading
import time
from pathlib import Path
from loguru import logger


def run_test_command(command_name, delay=0):
    """Run a test command after a delay."""
    if delay > 0:
        logger.info(f"{command_name}: Waiting {delay}s before starting...")
        time.sleep(delay)

    logger.info(f"{command_name}: Starting test run...")
    start_time = time.time()

    result = subprocess.run(
        [
            "uv",
            "run",
            "python",
            "scripts/test_runner_with_lock.py",
            "test/test_runnables.py",
            "-v",
        ],
        cwd=Path(__file__).parent.parent,
        capture_output=True,
        text=True,
    )

    elapsed = time.time() - start_time
    logger.info(
        f"{command_name}: Completed in {elapsed:.2f}s with return code {result.returncode}"
    )

    if result.stdout:
        logger.info(f"{command_name} stdout:\n{result.stdout}")
    if result.stderr:
        logger.warning(f"{command_name} stderr:\n{result.stderr}")

    return result


def test_concurrent_runs():
    """Test that concurrent runs properly wait for each other."""
    logger.info("Testing concurrent pytest runs with lock mechanism...")

    # Create threads to run tests concurrently
    threads = []

    # Start first test immediately
    t1 = threading.Thread(target=run_test_command, args=("Test Run 1", 0))
    threads.append(t1)

    # Start second test after 0.5 seconds (should see waiting message)
    t2 = threading.Thread(target=run_test_command, args=("Test Run 2", 0.5))
    threads.append(t2)

    # Start third test after 1 second (should also wait)
    t3 = threading.Thread(target=run_test_command, args=("Test Run 3", 1))
    threads.append(t3)

    # Start all threads
    for t in threads:
        t.start()

    # Wait for all threads to complete
    for t in threads:
        t.join()

    logger.success("✅ Concurrent test simulation completed!")
    logger.info(
        "Check the logs above to verify that tests waited for each other properly."
    )


if __name__ == "__main__":
    test_concurrent_runs()
