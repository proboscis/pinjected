# Remaining Improvements after API Migration

## Background
We've completed the migration of our deprecated functions (`instances()`, `providers()`, `classes()`) to the new `design()` API. During this process, we identified several areas for future improvement that are not directly related to the core migration task.

## Areas for Improvement

### 1. Test Package Refactoring
- Fix `dummy_config_creator_for_test` which currently has the `@injected` decorator removed as a workaround
- Resolve `Injected.bind()` issues in test package initialization
- Key files: `pinjected/test_package/__init__.py`, `pinjected/test_package/child/module1.py`

### 2. Warning Resolution
- Update deprecated PEP 485 typing hints to use `beartype.typing` instead of `typing`
- Migrate Pydantic V1 style `@validator` decorators to V2 style `@field_validator`
- Fix pytest collection warnings for test classes with `__init__` constructors

### 3. Documentation and Error Messages
- Expand migration guide with more complex examples
- Enhance runtime warning messages to include specific migration guidance
- Improve type hints for better IDE integration

### 4. Async Pattern Standardization
- Define consistent async patterns across the codebase
- Improve async support in test environments

## Implementation Ideas
- Create an automated migration tool
- Enhance runtime warnings with specific guidance
- Investigate circular dependency behavior differences with the new API

## Related Work
- PR #xx: Migration from deprecated functions to `design()`
- Issue #xx: Test suite improvements

## Acceptance Criteria
- [ ] All warnings are resolved or documented with clear reasons for deferring fixes
- [ ] Test package fully works with the new API
- [ ] Documentation is updated to reflect best practices with the new API
- [ ] Type hints are consistent and follow modern Python typing practices

## Non-Goals
- Complete rewrite of test infrastructure
- Breaking changes to public APIs

/cc @proboscis