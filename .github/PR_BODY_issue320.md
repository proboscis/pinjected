# fix(test-runner): prevent Error 143 by hardening lock-based pytest runner; add diagnostics and unit tests (closes #320)

Link to Devin run: https://app.devin.ai/sessions/99d5de5ecc3b4f8695d96e269a00adb5
Requested by: @proboscis (Proboscis)

Summary
- Harden scripts/test_runner_with_lock.py to prevent SIGTERM-caused Error 143 and reduce resource conflicts.
- Add:
  - SIGTERM/SIGINT handlers that terminate child pytest process and release file lock.
  - Environment default PYTHONFAULTHANDLER=1 for richer crash diagnostics.
  - Minor cleanup after child completion (gc + brief sleep) to mitigate spikes.
  - Consistent file-lock guarded test sequencing across packages.
- Add unit tests: test/test_test_runner_with_lock_enhanced.py covering:
  - Running with env defaults.
  - Signal handling and exit code path.
  - No-tests-found handling within make-test logic.

Before/After: Visibility Improvements
- Before: sporadic Error 143 termination with minimal diagnostics and potential stale lock.
- After:
  - Clear log lines for lock acquisition and waiting progress.
  - Proper termination path on SIGTERM/SIGINT with lock released.
  - Fault handler enabled to dump tracebacks on abrupt terminations.

Local Test Evidence
- Focused unit tests:
  - 3 passed for enhanced runner logic.
- Full suite run via the runner completed end-to-end without Error 143. Many tests fail, but the suite no longer terminates with 143.
- Attached/captured local run log:
  - /home/ubuntu/test_output_issue320.txt

Example Logs (excerpts)
```
... Running make test logic with file locking...
... Syncing all packages...
... Testing main pinjected package...
... ⏳ Another pytest instance is currently running. Waiting for it to complete...
... Still waiting... (5s elapsed)
```

Notes
- Scope intentionally limited to runner/test flow; CI YAMLs unchanged.
- Uses uv per repo policy; no pip usage.
- Makefile targets untouched; behavior exercised through script invoked by make test target.

## CI Triage and Status

Current CI summary for PR #325:
- Failed jobs:
  - build-and-test
  - test (3.11)
- Canceled jobs:
  - test (3.10)
  - test (3.12)
  - test (3.13)

From test (3.11) logs (Run tests with coverage):
- 3 errors during collection, unrelated to the test runner changes:
  - ide-plugins/pycharm/test_iproxy.py — TypeError: IProxy.__init__() missing 1 required positional argument: 'value'
  - packages/pinjected-linter/tests/test_cli_doc_feature.py — error during collection (see CI logs)
  - test/test_console_run_helper.py — error during collection (see CI logs)

Observation:
- These errors occur in modules not modified by this PR and appear unrelated to the lock-based pytest runner changes.
- The enhanced runner unit tests pass locally (3 passed).
- A full local run via the enhanced runner completed without Error 143.

Branch sync:
- Merged latest main into the feature branch to pick up recent fixes and reduce unrelated CI noise. CI will be re-run after pushing.

Next steps:
- Re-run CI after syncing with main and monitor outcomes.
- Keep the scope focused on the test runner reliability improvements (lock, signal handling, process cleanup). If unrelated test failures persist, they will be documented but not modified within this PR.
