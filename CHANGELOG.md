# Changelog

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