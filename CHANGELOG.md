# Changelog

## 0.2.246-beta.2 (2025-03-23)

### Changed
- Bumped beta version for PyPI publishing

## 0.2.246-beta.1 (2025-03-22)

### Changed
- Added beta prefix to version for PyPI publishing preparation

## 0.2.246 (2025-03-19)

### Fixed
- Fixed save_as_html in visualize_di.py
- Improved performance in run_injected.py by commenting out tree visualization output
- Fixed import ordering in run_injected.py

## 0.2.245 (2025-03-19)

### Fixed
- Fixed exception handling in save_as_html method by returning the result from nx.save_as_html_at

## 0.2.244 (2025-03-18)

### Fixed
- Improved exception handling in AsyncResolver provide method
- Added comprehensive type annotations to address deprecation warnings

## 0.2.243 (2025-03-15)

### Changed
- Replaced deprecated API functions (`instances()`, `providers()`, `classes()`) with unified `design()` function
- Fixed all tests to work with the new API, achieving 100% test pass rate
- Added documentation for API migration patterns in `issues/migration-patterns.md`

### Fixed
- Fixed variable name conflict in `injected_pytest` module by using import aliasing
- Fixed async function handling in test runner modules
- Added pytest-asyncio configuration in pyproject.toml for proper async test execution

## 0.2.242 (2025-03-11)

### Added
- Added experimental v3 proxy-based decorators for better IDE type hints

## 0.2.241 (2025-03-10)

### Changed
- Deprecated annotations in favor of type hints for dependency injection
- Simplified exception handlers by removing logger dependency

## 0.2.240 (2025-03-10)

### Fixed
- Improved ExceptionGroup handling in AsyncResolver provide method
- Added compatibility layer to handle different ExceptionGroup implementations across Python versions

## 0.2.239 (2025-03-07)

### Added
- Exposed test utility functions in test package: `test_tree`, `test_current_file`, and `test_tagged`

### Changed
- Added type annotation for `test_runnable` in test module
