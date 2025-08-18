# PINJ040: Deprecated @injected_pytest Decorator

## Import Instructions

To use `@injected_pytest` (though deprecated), import it from one of these locations:

```python
# Recommended import path:
from pinjected.test import injected_pytest

# Alternative import path:
from pinjected.test.injected_pytest import injected_pytest
```

## Overview

The `@injected_pytest` decorator is deprecated. Use the modern pytest fixture integration with `register_fixtures_from_design` instead.

## Rationale

The `@injected_pytest` decorator had several limitations:

1. **Limited Scoping**: No control over fixture lifecycle (function, class, module, session)
2. **No Dependency Sharing**: Each test got isolated dependencies, preventing shared state
3. **Poor Integration**: Difficult to mix with regular pytest fixtures
4. **Verbose**: Required decorating every test function
5. **Type Safety**: Limited IDE support and type inference

The new `register_fixtures_from_design` approach provides:

- Full pytest fixture scoping (function, class, module, session)
- Proper dependency sharing within the same scope
- Seamless mixing with regular pytest fixtures
- Register once, use everywhere
- Better IDE support and type hints
- Cleaner test code without decorators

## Examples

### ❌ Incorrect (Deprecated)

```python
# Correct import paths (choose one):
from pinjected.test import injected_pytest
# OR
from pinjected.test.injected_pytest import injected_pytest

from pinjected import injected

@injected
def database():
    return {"connected": True}

@injected
def user_service(database):
    return UserService(database)

# Deprecated decorator usage
@injected_pytest
def test_user_creation(user_service, database):
    user = user_service.create_user("test@example.com")
    assert user.id in database

@injected_pytest
async def test_async_operation(user_service):
    result = await user_service.async_method()
    assert result is not None
```

### ✅ Correct (Modern API)

```python
# In conftest.py or at module level
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

# Register all bindings as pytest fixtures
register_fixtures_from_design(test_design)

# Now write tests without decorators
def test_user_creation(user_service, database):
    user = user_service.create_user("test@example.com")
    assert user.id in database

@pytest.mark.asyncio
async def test_async_operation(user_service):
    result = await user_service.async_method()
    assert result is not None
```

## Auto-Fix

This rule does not provide auto-fix. The migration requires manual refactoring to:
- Identify all injected dependencies across test files
- Create appropriate design objects
- Choose the right fixture scope
- Register fixtures at the appropriate level (module, conftest.py, etc.)

Manual migration ensures proper fixture organization and scoping decisions.

## Migration Steps

1. **Identify all dependencies** used in `@injected_pytest` decorated tests
2. **Create a test design** with all dependencies:
   ```python
   test_design = design(
       database=test_database,
       user_service=user_service,
       # ... other dependencies
   )
   ```
3. **Register fixtures** in conftest.py or module level:
   ```python
   register_fixtures_from_design(test_design)
   ```
4. **Remove decorators** from test functions
5. **Add `@pytest.mark.asyncio`** to async tests

## Common Patterns

### Module-Level Registration

```python
# test_user_service.py
from pinjected import design
from pinjected.test import register_fixtures_from_design

test_design = design(
    database=test_database,
    user_service=user_service,
)

register_fixtures_from_design(test_design)

# Tests can now use fixtures directly
def test_create_user(user_service, database):
    user = user_service.create_user("test@example.com")
    assert user.id in database
```

### Scoped Fixtures for Expensive Resources

```python
# Register expensive resources with session scope
register_fixtures_from_design(
    expensive_design,
    scope="session",
    include={"database", "ml_model"}
)
```

### Mixing with Regular Pytest Fixtures

```python
@pytest.fixture
def test_data():
    return {"id": 123, "name": "Test"}

@pytest.mark.asyncio
async def test_mixed(user_service, test_data):
    # Use both pinjected and regular fixtures
    user = await user_service.create(test_data)
    assert user.name == test_data["name"]
```

## Configuration

```toml
[rules.PINJ040]
enabled = true
severity = "warning"
```

## See Also

- [Pytest Fixtures Documentation](https://docs.pytest.org/en/stable/fixture.html)
- [Pinjected Pytest Integration Guide](../../../docs/pytest-fixtures.md)