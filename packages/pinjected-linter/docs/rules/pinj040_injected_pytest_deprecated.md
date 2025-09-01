# PINJ040: Deprecated register_fixtures_from_design Function

## Import Instructions

To use `@injected_pytest` (the recommended approach), import it from one of these locations:

```python
# Recommended import path:
from pinjected.test import injected_pytest

# Alternative import path:
from pinjected.test.injected_pytest import injected_pytest
```

## Quick usage with a test design

This is the recommended way to inject dependencies using a design:

```python
from pinjected import design
from pinjected.test import injected_pytest

di = design(x=123)

@injected_pytest(di)
def test_x(x):
    assert x == 123
```

Imports:
- from pinjected import design
- from pinjected.test import injected_pytest

## Overview

The `register_fixtures_from_design` function is deprecated. Use the modern `@injected_pytest` decorator instead.

## Rationale

The `register_fixtures_from_design` function had several limitations:

1. **Complex Setup**: Required understanding of pytest fixture scoping and registration
2. **Indirect Dependency Injection**: Dependencies were not explicitly visible in test signatures
3. **Fixture Conflicts**: Could conflict with existing pytest fixtures with same names
4. **Limited Flexibility**: Difficult to override dependencies for specific tests
5. **Maintenance Overhead**: Required managing fixture registration separately from test logic

The modern `@injected_pytest` approach provides:

- Direct dependency injection into test function parameters
- Explicit dependency visibility in test signatures
- Easy test-specific dependency overrides
- Seamless async test support
- Integration with pinjected's meta context system
- Cleaner test logic without separate fixture registration

## Examples

### ❌ Incorrect (Deprecated)

```python
# Deprecated register_fixtures_from_design usage
from pinjected import design, injected
from pinjected.test import register_fixtures_from_design
import pytest

@injected
def database():
    return {"connected": True}

@injected
def user_service(database):
    return UserService(database)

# Create test design
test_design = design(
    database=database,
    user_service=user_service,
)

# Deprecated fixture registration
register_fixtures_from_design(test_design)

# Tests using fixtures
def test_user_creation(user_service, database):
    user = user_service.create_user("test@example.com")
    assert user.id in database

@pytest.mark.asyncio
async def test_async_operation(user_service):
    result = await user_service.async_method()
    assert result is not None
```

### ✅ Correct (Modern API)

```python
# Modern @injected_pytest usage
from pinjected import design, injected
from pinjected.test import injected_pytest

@injected
def database():
    return {"connected": True}

@injected
def user_service(database):
    return UserService(database)

# Create test design
test_design = design(
    database=database,
    user_service=user_service,
)

# Use @injected_pytest decorator
@injected_pytest(test_design)
def test_user_creation(user_service, database):
    user = user_service.create_user("test@example.com")
    assert user.id in database

@injected_pytest(test_design)
async def test_async_operation(user_service):
    result = await user_service.async_method()
    assert result is not None
```

## Auto-Fix

This rule does not provide auto-fix. The migration requires manual refactoring to:
- Remove `register_fixtures_from_design` calls
- Add `@injected_pytest` decorators to test functions
- Update test function signatures to receive dependencies as parameters
- Ensure design objects are properly defined at module level

Manual migration ensures proper dependency injection setup and test organization.

## Migration Steps

1. **Identify all dependencies** used in tests with `register_fixtures_from_design`
2. **Create a test design** with all dependencies:
   ```python
   test_design = design(
       database=test_database,
       user_service=user_service,
       # ... other dependencies
   )
   ```
3. **Remove `register_fixtures_from_design` calls** from conftest.py or module level
4. **Add `@injected_pytest` decorators** to test functions:
   ```python
   @injected_pytest(test_design)
   def test_something(database, user_service):
       pass
   ```
5. **Remove `@pytest.mark.asyncio`** from async tests (handled automatically by `@injected_pytest`)

## Common Patterns

### Module-Level Design with @injected_pytest

```python
# test_user_service.py
from pinjected import design
from pinjected.test import injected_pytest

test_design = design(
    database=test_database,
    user_service=user_service,
)

# Use @injected_pytest decorator on each test
@injected_pytest(test_design)
def test_create_user(user_service, database):
    user = user_service.create_user("test@example.com")
    assert user.id in database
```

### Test-Specific Dependency Overrides

```python
# Override specific dependencies for individual tests
@injected_pytest(test_design.override(database=mock_database))
def test_with_mock_database(user_service, database):
    # Uses mock_database instead of the default
    user = user_service.create_user("test@example.com")
    assert user.id in database
```

### Async Tests with @injected_pytest

```python
# Async tests work automatically without @pytest.mark.asyncio
@injected_pytest(test_design)
async def test_async_operation(user_service):
    result = await user_service.async_method()
    assert result is not None
```

## Configuration

```toml
[rules.PINJ040]
enabled = true
severity = "warning"
```

## See Also

- [PINJ052: Deprecated register_fixtures_from_design](pinj052_deprecated_register_fixtures.md)
- [Pinjected @injected_pytest Documentation](../../../docs/how_to_use_pinjected.md)
