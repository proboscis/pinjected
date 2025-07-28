# PINJ043: No design() in Test Functions

## Overview

The `design()` context manager should not be used inside test functions. Test designs should be created at module level and converted to pytest fixtures using `register_fixtures_from_design()`.

## Rationale

Using `design()` inside test functions is not supported and will not work:

1. **Not Supported**: The `with design()` context manager only works for IProxy entrypoint declarations, not for test dependency resolution
2. **Non-functional Code**: This pattern will result in runtime errors or undefined behavior
3. **Wrong Approach**: Tests require proper dependency injection through pytest fixtures or `@injected_pytest`
4. **Against Design**: Goes against pinjected's architecture for test dependency management

The correct pattern is to use `register_fixtures_from_design()` which:
- Provides full pytest fixture scoping (function, class, module, session)
- Enables proper dependency sharing within the same scope
- Integrates seamlessly with regular pytest fixtures
- Supports better IDE integration and type hints
- Keeps tests clean without decorators

## Examples

### ❌ Incorrect

```python
from pinjected import design

def test_user_creation():
    # VIOLATION: design() inside test function - THIS DOES NOT WORK!
    # The with design() context manager is only for IProxy entrypoints
    with design() as d:
        d.provide("user_service", MockUserService())
        d.provide("database", MockDatabase())
    
    # This doesn't inject anything - user_service and database are undefined
    user = user_service.create_user("test@example.com")  # NameError!
    assert user.id in database

def test_another_violation():
    # VIOLATION: Trying to use design to get dependencies - WRONG!
    d = design(
        user_service=MockUserService(),
        database=MockDatabase()
    )
    # This doesn't make dependencies available in test scope
    user = user_service.create_user("test@example.com")  # NameError!

@pytest.mark.parametrize("value", [1, 2, 3])
def test_parametrized(value):
    # VIOLATION: design() in test - WILL NOT WORK!
    test_design = design(service=MockService())
    # service is not available in test function scope
    assert service.process(value) > 0  # NameError!
```

### ✅ Correct - Recommended Approach Using register_fixtures_from_design

```python
from pinjected import design, instances
from pinjected.test import register_fixtures_from_design
import pytest

# Create design at module level
test_design = design(
    user_service=MockUserService(),
    database=MockDatabase()
)

# Or use instances() for multiple dependencies
test_design += instances(
    async_service=MockAsyncService(),
    service=MockService()
)

# Register as pytest fixtures (recommended approach)
register_fixtures_from_design(test_design)

# Now write clean tests using fixtures
def test_user_creation(user_service, database):
    user = user_service.create_user("test@example.com")
    assert user.id in database

@pytest.mark.asyncio
async def test_async_operation(async_service):
    result = await async_service.do_something()
    assert result is not None

@pytest.mark.parametrize("value", [1, 2, 3])
def test_parametrized(value, service):
    # service is efficiently reused across all parameters
    assert service.process(value) > 0
```

### ✅ Alternative Approach Using @injected_pytest

While `@injected_pytest` is still supported, `register_fixtures_from_design()` is the recommended approach for better pytest integration:

```python
from pinjected.test import injected_pytest
from pinjected import design, instance

# Mock implementations for testing
@instance
def mock_user_service():
    return MockUserService()

@instance  
def mock_database():
    return MockDatabase()

# Test with custom design override
test_design = design(
    user_service=mock_user_service,
    database=mock_database,
    async_service=MockAsyncService()
)

# Using @injected_pytest (supported but not recommended)
@injected_pytest(test_design)
def test_user_creation(user_service, database):
    # Dependencies are automatically injected
    user = user_service.create_user("test@example.com")
    assert user.id in database

@injected_pytest(test_design)
async def test_async_operation(async_service):
    # async_service is injected from test_design
    result = await async_service.do_something()
    assert result is not None
```

## Common Patterns

### Using conftest.py for Shared Designs

```python
# conftest.py
from pinjected import design, instances
from pinjected.test import register_fixtures_from_design

# Shared test design for all tests
shared_design = design(
    database=MockDatabase(),
    cache=MockCache(),
    logger=MockLogger()
)

# Register with appropriate scope
register_fixtures_from_design(
    shared_design,
    scope="session"  # Share expensive resources across all tests
)
```

### Module-Specific Test Design

```python
# test_user_service.py
from pinjected import design
from pinjected.test import register_fixtures_from_design

# Module-specific mocks
class MockEmailService:
    def __init__(self):
        self.sent_count = 0
    
    def send(self, to, subject, body):
        self.sent_count += 1

# Create module-specific design
user_test_design = design(
    user_service=UserService(),
    email_service=MockEmailService()
)

# Register fixtures for this module
register_fixtures_from_design(user_test_design)

# Clean tests using fixtures
def test_user_registration(user_service, email_service):
    user = user_service.register("test@example.com")
    assert email_service.sent_count == 1
```

### Scoped Fixtures for Expensive Resources

```python
from pinjected import design, instance
from pinjected.test import register_fixtures_from_design

@instance
def ml_model():
    # Expensive model loading
    return load_large_model()

@instance
def database_connection():
    # Expensive connection setup
    return create_db_connection()

expensive_design = design(
    ml_model=ml_model,
    database=database_connection
)

# Register with session scope to load once per test session
register_fixtures_from_design(
    expensive_design,
    scope="session",
    include={"ml_model", "database"}
)
```

### Conditional Test Setup

```python
# Module level conditional design
import os
from pinjected import design
from pinjected.test import register_fixtures_from_design

# Build design conditionally at module level
if os.getenv("USE_MOCK_DB"):
    test_db = MockDatabase()
else:
    test_db = TestDatabase()

conditional_design = design(database=test_db)

# Register the conditional fixtures
register_fixtures_from_design(conditional_design)

# Use in tests
def test_with_conditional_db(database):
    # database is either mock or real based on env
    assert database.is_connected()
```

### Testing @injected Functions

```python
from pinjected import design, injected
from pinjected.test import register_fixtures_from_design

# Function to test (uses @injected)
@injected
def fetch_user_data(database, cache, logger, /, user_id: str):
    cached_data = cache.get(f"user:{user_id}")
    if cached_data:
        logger.info(f"Cache hit for user {user_id}")
        return cached_data
    
    data = database.get(f"user:{user_id}")
    if data:
        cache.set(f"user:{user_id}", data, ttl=3600)
    return data

# Test design with all mocks
test_design = design(
    database=MockDatabase(),
    cache=MockCache(),
    logger=MockLogger(),
    fetch_user_data=fetch_user_data  # Include the function to test
)

register_fixtures_from_design(test_design)

def test_fetch_user_data_cache_miss(fetch_user_data, database, cache, logger):
    # Set up test data
    user_id = "user123"
    user_data = {"name": "Test User", "email": "test@example.com"}
    database.data[f"user:{user_id}"] = user_data
    
    # Execute function
    result = fetch_user_data(user_id)
    
    # Verify behavior
    assert result == user_data
    assert cache.cache.get(f"user:{user_id}") == user_data
    assert any("Cache miss" in log for log in logger.logs)
```

## Migration Guide

To fix violations of this rule, migrate to using `register_fixtures_from_design()` or `@injected_pytest`:

### Option 1: Migrate to register_fixtures_from_design (Recommended)

```python
# Before (design() in test - NOT WORKING)
def test_something():
    with design() as d:
        d.provide("service", MyService())
        d.provide("database", MockDatabase())
    # service and database are NOT in scope - test fails
    result = service.method()  # NameError!

# After (using register_fixtures_from_design)
from pinjected.test import register_fixtures_from_design
from pinjected import design

test_design = design(
    service=MyService(),
    database=MockDatabase()
)
register_fixtures_from_design(test_design)

def test_something(service, database):
    # service and database are injected as pytest fixtures
    result = service.method()
    assert result == expected
```

### Option 2: Migrate to @injected_pytest (Alternative)

```python
# Before (design() in test - NOT WORKING)
def test_something():
    test_design = design(service=MyService())
    # service is NOT available in test scope
    result = service.method()  # NameError!

# After (using @injected_pytest)
from pinjected.test import injected_pytest
from pinjected import design

test_design = design(service=MyService())

@injected_pytest(test_design)
def test_something(service):
    result = service.method()
```

### Key Migration Points

1. **Remove with design() blocks** from inside test functions
2. **Choose your testing approach**:
   - Use `@injected_pytest` for pinjected-native testing (recommended)
   - Use `register_fixtures_from_design()` for pytest fixture integration
3. **Update test function signatures** to receive dependencies as parameters
4. **Create designs at module level**, not inside functions

## Configuration

```toml
[rules.PINJ043]
enabled = true
severity = "error"
```

## See Also

- [PINJ028: No design() in @injected Functions](./pinj028_no_design_in_injected.md)
- [Pinjected Testing Guide](https://pinjected.readthedocs.io/en/latest/testing.html)
- [Pytest Fixtures Documentation](https://docs.pytest.org/en/stable/fixture.html)