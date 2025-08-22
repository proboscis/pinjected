CI triage for PR #325 (issue #320)

Summary
- Purpose: Improve test runner reliability to eliminate Error 143 terminations and resource conflicts.
- Scope (Option A): scripts/test_runner_with_lock.py, its unit tests, and Makefile test entry alignment only. No CI workflow changes. Uses uv.
- Status: Runner unit tests pass; full runner flow executes end-to-end without Error 143. CI still shows unrelated collection errors.

Local verification
- Focused unit tests:
  - uv run pytest -q test/test_test_runner_with_lock_enhanced.py
  - Result: 3 passed in ~1s
- Full suite via enhanced runner:
  - uv run python scripts/test_runner_with_lock.py --make-test | tee /home/ubuntu/test_output_issue320.txt
  - Result: No Error 143. Suite completes end-to-end. Some tests fail unrelated to runner.
- Makefile alignment:
  - test-cov updated to use: uv run python scripts/test_runner_with_lock.py --make-test -v
  - Avoids broad “pytest .” and ensures sync + targeted collection.

CI findings
- Current checks: 2 failed, 3 canceled.
  - Failed:
    - build-and-test
    - test (3.10) / test (3.11) depending on matrix runs
  - Canceled:
    - remaining Python versions in matrix
- Errors consistently observed:
  - ide-plugins/pycharm/test_iproxy.py — TypeError: IProxy.__init__() missing 1 required positional argument: 'value'
  - packages/pinjected-linter/tests/test_cli_doc_feature.py — ModuleNotFoundError: No module named 'click'
  - test/test_console_run_helper.py — collection/import errors
- These paths are outside the runner and not modified by this PR.

Reproduction notes
- Repository standards:
  - Use uv for all Python execution.
  - Sync before tests: uv sync --all-packages or make sync.
- Python versions:
  - CI matrix includes 3.10–3.13; runner changes are version-agnostic.
- Reproduce locally:
  - make sync
  - uv run pytest -q test/test_test_runner_with_lock_enhanced.py
  - uv run python scripts/test_runner_with_lock.py --make-test

Diagnostics added by this PR
- Signal handling for SIGTERM/SIGINT with child termination and safe lock release.
- Default PYTHONFAULTHANDLER=1 to capture tracebacks on abrupt exits.
- Light cleanup post child termination (gc + brief sleep).
- Consistent lock-guarded sequencing with progress logging.

Conclusion
- Runner reliably avoids exit code 143 and releases locks under termination.
- Makefile now uses the lock-based flow for test-cov to ensure deterministic orchestration.
- CI failures are unrelated to the runner changes and should be addressed in separate follow-up PRs.
