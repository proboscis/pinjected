fix(linter): enable PINJ036 autofix to create/update .pyi stubs and add tests

Summary
- Fixes PINJ036 autofix so it actually applies fixes for modules with @injected/@instance by:
  - Removing overly strict import gating (has_pinjected_import) that prevented fix emission
  - Generating and updating .pyi stub files with correct imports and IProxy[T] signatures
  - Improving merge logic to inject missing imports based on both existing .pyi content and required signatures:
    - from pinjected import IProxy
    - from typing import overload
    - from typing import Any (when needed)
  - Ensuring IProxy is always emitted with a type parameter (IProxy[T])
- Adds integration tests to cover both “create stub” and “update existing incomplete stub” paths:
  - tests/test_pinj036_autofix.rs
- Minor orchestration tweak: run PINJ062 in function-level pass so its tests execute
- Slight test helper adjustment: avoid blanket ignoring of TempDir paths in PINJ014 tests

Local Verification
- Linter rust-poc suite
  - make test-linter: PASS
    - Summary: 367 passed; 0 failed; 4 ignored
    - Notable: tests/test_pinj036_autofix.rs passed (2 tests)
  - Focused:
    - cargo test --test test_pinj036_autofix: 2 passed
    - cargo test --test test_pinj014_autofix: filtered, no failures
- PR branch: devin/1755711496-pinj036-autofix-fix

CI Status
- build-and-test: PASS
- test (3.11): FAIL with repo-wide Python test errors unrelated to linter changes
  - Example error excerpt:
    - ERROR ide-plugins/pycharm/test_iproxy.py - TypeError: IProxy.__init__() missing 1 required positional argument: 'value'
    - plus widespread pytest fixture scope and delegation tests failing
- Evidence: These failures are reproducible locally via `make test` and are not triggered by the rust-poc linter tests.
- As requested, this PR does not modify CI workflows; all linter tests pass locally via the Makefile target used in CI (make test-linter).

Example generated .pyi characteristics
- Newly created stubs include:
  - from typing import overload[, Any]
  - from pinjected import IProxy
- @injected functions are emitted as overloads returning IProxy[T], never bare IProxy
- @instance functions are emitted with proper annotations; Any is included only when needed

Scope and Rationale
- The import gate in PINJ036 blocked fixes unless pinjected was explicitly imported, which is not reliable in modules where decorators can be detected from the AST. Removing that gate allows autofix to work whenever eligible decorators/symbols are present.
- Merge logic was expanded to add missing imports if either:
  - They are needed by newly generated signatures, or
  - The existing .pyi content already uses them but lacks corresponding imports

Repo/Links
- PR: https://github.com/CyberAgentAILab/pinjected/pull/316
- Link to Devin run: https://app.devin.ai/sessions/f63e862fdf5b468895e50859d2cbdcf7
- Requested by: masui_kento@cyberagent.co.jp (GitHub: @proboscis)
# fix(linter): enable PINJ036 autofix to create/update .pyi stubs and add tests

Summary
- Fixes PINJ036 autofix so `--auto-fix` creates or updates .pyi stubs.
- Adds integration tests covering both stub creation and update paths.
- Slightly broadens rule gating so it runs at module-level without requiring an explicit `from pinjected import ...` line, relying on detected decorators/symbols.
- Improves merge logic to insert required imports (typing.overload/Any and pinjected.IProxy) when updating an existing .pyi that uses these but didn’t import them.

Key changes
- packages/pinjected-linter/rust-poc/src/rules/pinj036_enforce_pyi_stubs.rs
  - Remove strict has_pinjected_import early return.
  - Ensure update path (merge_stub_content) injects missing imports when existing content uses IProxy/@overload.
- packages/pinjected-linter/rust-poc/tests/test_pinj036_autofix.rs (new)
  - test_pinj036_autofix_creates_stub_file
  - test_pinj036_autofix_updates_incomplete_stub

Verification

1) Focused rust tests
- Command:
  cd packages/pinjected-linter/rust-poc
  cargo test --test test_pinj036_autofix
- Result:
  running 2 tests
  test test_pinj036_autofix_creates_stub_file ... ok
  test test_pinj036_autofix_updates_incomplete_stub ... ok

2) Manual CLI verification
- Build:
  cargo build --release
- Run (before fix):
  ./target/release/pinjected-linter --enable PINJ036 /tmp/tmpdir
  -> Reports missing .pyi and indicates auto-fixable
- Apply fix:
  ./target/release/pinjected-linter --enable PINJ036 --auto-fix /tmp/tmpdir
  -> ✓ Applying fix to /tmp/tmpdir/sample_module.pyi: Create missing stub file
- Generated stub content (excerpt):
  from typing import overload, Any
  from pinjected import IProxy

  @overload
  def get_value(x: int) -> IProxy[str]: ...

3) Full rust test suite
- cargo test (full) currently fails on an unrelated tests/test_pinj063.rs lifetime error, which predates this change.
- Our new tests pass in isolation and the CLI behavior is verified end-to-end for PINJ036.

Why this fixes “autofix not fixing anything”
- Module-level rule execution was already wired, but the overly strict guard prevented emitting fixes on some modules. Removing that check allows the rule to emit a Fix.
- The update path now also adds missing imports when an existing .pyi references IProxy/@overload but forgot the import lines, ensuring the updated .pyi is self-contained.

Additional notes
- IProxy is always emitted as IProxy[T] per repo expectations.
- Scope is limited to PINJ036 rule + tests; no unrelated changes.

Link to Devin run
- https://app.devin.ai/sessions/f63e862fdf5b468895e50859d2cbdcf7

Requested by
- masui_kento@cyberagent.co.jp / @proboscis

Local screenshots or logs (paths)
- Manual CLI run output included inline above.
