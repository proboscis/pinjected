# Future Improvements for Pinjected

After completing the migration from deprecated functions (`instances()`, `providers()`, `classes()`) to `design()`, the following areas need improvement:

## 1. Test Package Refactoring

### 1.1 Fix `dummy_config_creator_for_test`
- **Issue**: Currently avoiding errors by removing the `@injected` decorator
- **Solution**: Properly fix the dependency binding mechanism to work with the updated API
- **Files**:
  - `pinjected/test_package/__init__.py`
  - Related test configuration files

### 1.2 Resolve `Injected.bind()` Issues in Test Package
- **Issue**: Multiple binding issues in test package initialization
- **Goal**: Make test package work with both old and new APIs during transition
- **Files**:
  - `pinjected/test_package/__init__.py`
  - `pinjected/test_package/child/module1.py`

## 2. Address Remaining Warnings

### 2.1 Fix PEP 585 Deprecation Warnings
- **Issue**: Using deprecated `typing` module imports instead of PEP 585 compliant imports
- **Solution**: Replace `typing` imports with `beartype.typing` where appropriate
- **Example Warning**:
  ```
  BeartypeDecorHintPep585DeprecationWarning: Function return PEP 484 type hint typing.List[...] deprecated by PEP 585
  ```
- **Files**:
  - `pinjected/runnables.py`
  - `pinjected/test_helper/test_aggregator.py`
  - Other files showing similar warnings

### 2.2 Update Pydantic Validators
- **Issue**: Using deprecated Pydantic V1 style `@validator` decorators
- **Solution**: Migrate to Pydantic V2 style `@field_validator` decorators
- **Example Warning**:
  ```
  PydanticDeprecatedSince20: Pydantic V1 style `@validator` validators are deprecated.
  ```
- **Files**:
  - `pinjected/runnables.py`

### 2.3 Fix Pytest Collection Warnings 
- **Issue**: Cannot collect test classes with `__init__` constructor
- **Solution**: Restructure test classes to follow pytest conventions
- **Files**:
  - `pinjected/test_helper/test_runner.py`
  - `pinjected/di/partially_injected.py`

## 3. Documentation and Best Practices

### 3.1 Expand Migration Guide
- **Status**: Initial version created in `issues/migration-patterns.md`
- **Improvements**:
  - Add more complex examples for nested designs
  - Include examples for async patterns
  - Show how to handle circular dependencies
  - Document common pitfalls and edge cases

### 3.2 Improve Type Hints
- **Issue**: Some areas lack proper type hints or use deprecated patterns
- **Solution**: Add/update type hints following modern Python typing practices
- **Benefits**: Better IDE integration and improved developer experience

## 4. Implementation Ideas

### 4.1 Automated Migration Tool
- **Idea**: Create a script that automatically migrates code from old API to new
- **Features**:
  - Pattern matching for common usage patterns
  - Automatic wrapping of callables with `Injected.bind()`
  - Interactive mode for handling ambiguous cases

### 4.2 Runtime Warning Insights
- **Idea**: Enhance warning messages to give specific guidance on migration
- **Example**:
  ```
  DeprecationWarning: 'providers()' is deprecated and will be removed in a future version. 
  Use 'design()' instead. Found in file.py:123. Suggested replacement:
  design(func=Injected.bind(lambda x: x))
  ```

## 5. Edge Cases to Investigate

### 5.1 Circular Dependencies with New API
- **Issue**: Circular dependencies might behave differently with `design()` API
- **Investigation**: Test and document any differences in behavior

### 5.2 Async Pattern Standardization
- **Issue**: Inconsistent async patterns across the codebase
- **Goal**: Define and implement consistent async patterns for all async operations

## Priority Order
1. Test Package Refactoring
2. PEP 585 Deprecation Warnings
3. Pydantic Validators
4. Documentation Improvements
5. Implementation Ideas
6. Edge Case Investigation