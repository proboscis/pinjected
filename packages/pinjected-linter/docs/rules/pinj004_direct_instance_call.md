# PINJ004: Direct Instance Call

## Overview

**Rule ID:** PINJ004  
**Category:** Usage  
**Severity:** Warning  
**Auto-fixable:** No

Avoid calling `@instance` functions directly. Use Pinjected's dependency injection or `design()` instead.

## Rationale

Functions decorated with `@instance` are meant to be dependency providers within Pinjected's injection system. Calling them directly bypasses the dependency injection framework and can lead to:

1. Loss of singleton behavior (creating multiple instances)
2. Bypassing dependency resolution and lifecycle management
3. Making testing and mocking more difficult
4. Breaking the dependency injection pattern
5. Potential issues with async dependency resolution

## Rule Details

This rule warns when an `@instance` decorated function is called directly with parentheses `()`.

### Examples of Violations

❌ **Bad:** Direct calls to @instance functions
```python
@instance
def database():
    return Database()

@instance
def cache():
    return RedisCache()

# Direct calls - bypassing injection
db = database()  # Warning: Direct call to @instance function
my_cache = cache()  # Warning: Direct call to @instance function

def some_function():
    # Also bad inside functions
    local_db = database()  # Warning
    return local_db.query("SELECT * FROM users")
```

✅ **Good:** Using dependency injection
```python
@instance
def database():
    return Database()

@instance
def cache():
    return RedisCache()

# Method 1: Use in @injected functions
@injected
def user_service(database, cache, /):
    # Dependencies are injected automatically
    return UserService(database, cache)

# Method 2: Use design() for configuration
config = design(
    db=database,  # Reference, not call
    cache=cache,  # Reference, not call
)

# Method 3: Use IProxy for entry points
from pinjected.di.iproxy import IProxy
get_users: IProxy = user_service.get_all_users()
```

## Common Patterns and Best Practices

### 1. Reference functions in design()
```python
# ❌ Bad - calling the functions
config = design(
    database=database(),  # Direct call
    cache=cache(),        # Direct call
)

# ✅ Good - referencing the functions
config = design(
    database=database,    # Function reference
    cache=cache,          # Function reference
)
```

### 2. Use @injected for dependency consumption
```python
# ❌ Bad - manual dependency creation
def process_data(data):
    db = database()  # Direct call
    cache = cache()  # Direct call
    # Process...

# ✅ Good - dependency injection
@injected
def process_data(database, cache, /, data):
    # Dependencies are injected
    # Process...
```

### 3. Testing with dependency injection
```python
# ❌ Bad - hard to test
def get_user(user_id):
    db = database()  # Direct call makes mocking difficult
    return db.get_user(user_id)

# ✅ Good - testable
@injected
def get_user(database, /, user_id):
    return database.get_user(user_id)

# Easy to test with mock
test_design = design(
    database=lambda: MockDatabase(),
)
```

## Exceptions

There are some valid cases where direct calls might be necessary:

1. **Initialization/Bootstrap code:**
```python
# OK in main/initialization
if __name__ == "__main__":
    # Direct call acceptable for bootstrap
    app = application()
    app.run()
```

2. **Testing the instance function itself:**
```python
def test_database_instance():
    # OK for testing the provider itself
    db = database()
    assert isinstance(db, Database)
```

## Configuration

This rule has no configuration options.

## When to Disable

You might want to disable this rule if:
- You're in a migration phase from direct instantiation to dependency injection
- You have initialization code that needs direct access
- You're writing tests for the instance functions themselves

To disable for a specific line:
```python
db = database()  # noqa: PINJ004
```

To disable in configuration:
```toml
[tool.pinjected-linter]
disable = ["PINJ004"]
```

## Related Rules

- **PINJ010:** Design() usage patterns (proper use of design())

## See Also

- [Pinjected documentation on dependency injection](https://pinjected.readthedocs.io)
- [design() API reference](https://pinjected.readthedocs.io/design)

## Version History

- **1.0.0:** Initial implementation