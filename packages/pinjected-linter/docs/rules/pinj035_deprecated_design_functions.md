# PINJ035: No Deprecated Design Functions

## Overview

This rule detects usage of deprecated design functions (`instances()`, `providers()`, `classes()`, `destructors()`, and `injecteds()`) and provides migration guidance to the modern `design()` API. These functions were deprecated in pinjected 0.3.0.

## Rationale

The older API had multiple functions for different types of bindings, which led to:

1. **API Fragmentation**: Multiple functions doing similar things made the API harder to learn
2. **Inconsistent Behavior**: Different functions had slightly different semantics
3. **Limited Flexibility**: Couldn't easily mix different types of bindings
4. **Poor Composability**: Harder to combine designs from different sources

The modern `design()` API provides a unified, consistent interface for all dependency injection needs.

## Deprecated Functions

### 1. `instances(**kwargs)`
Used to register concrete instances or values. Each key-value pair represents a dependency name and its concrete instance.

### 2. `providers(**kwargs)`  
Used to register provider functions or `Injected` instances. Automatically wrapped callables in `Injected.bind()`.

### 3. `classes(**kwargs)`
Used to register classes for dependency injection. Similar to `instances()` but specifically for class types.

### 4. `destructors(**kwargs)`
Used to register cleanup functions for resources.

### 5. `injecteds(**kwargs)`
Used to register `Injected` instances directly.

## Migration Guide

### ❌ Incorrect (Deprecated)

```python
from pinjected import instances, providers, classes, destructors, injecteds
from pinjected import Injected

# Using instances()
config = instances(
    host="localhost",
    port=5432,
    debug=True
)

# Using providers()
def create_database():
    return DatabaseConnection()

def create_logger():
    return Logger()

services = providers(
    database=create_database,
    logger=create_logger
)

# Using classes()
class_bindings = classes(
    UserService=UserService,
    AuthService=AuthService
)

# Using destructors()
def cleanup_database(db):
    db.close()

cleanups = destructors(
    database=cleanup_database
)

# Using injecteds()
injected_bindings = injecteds(
    processor=Injected.bind(lambda db, logger: Processor(db, logger))
)

# Combining designs
final_design = config + services + class_bindings + cleanups + injected_bindings
```

### ✅ Correct (Modern API)

```python
from pinjected import design, injected, instance

# Replace instances() with design() directly
config = design(
    host="localhost",
    port=5432,
    debug=True
)

# Replace providers() - decorate functions with @injected
@injected
def database():
    return DatabaseConnection()

@injected
def logger():
    return Logger()

# Replace classes() - create @instance decorated factory functions
@instance
def user_service():
    return UserService()

@instance
def auth_service():
    return AuthService()

# Combine all into design()
service_design = design(
    database=database,      # Pass the @injected function
    logger=logger,          # Pass the @injected function
    user_service=user_service,    # Pass the @instance function
    auth_service=auth_service     # Pass the @instance function
)

# Replace destructors() - use context managers in @injected functions
@injected
def managed_database():
    """Database with automatic cleanup."""
    db = DatabaseConnection()
    try:
        yield db
    finally:
        db.close()

# Replace injecteds() - use design() directly
injected_design = design(
    processor=Injected.bind(lambda db, logger: Processor(db, logger))
)

# Combine designs
final_design = config + service_design + design(database=managed_database) + injected_design
```

## Specific Migration Patterns

### Migrating `instances()`
```python
# Old
config = instances(api_key="secret", timeout=30)

# New
config = design(api_key="secret", timeout=30)
```

### Migrating `providers()`
```python
# Old
def get_service():
    return Service()

services = providers(service=get_service)

# New
@injected
def service():
    return Service()

services = design(service=service)  # Pass the @injected function
```

### Migrating `classes()`
```python
# Old
bindings = classes(UserRepo=UserRepository, AuthService=AuthService)

# New
@instance
def user_repo():
    return UserRepository()

@instance
def auth_service():
    return AuthService()

bindings = design(
    user_repo=user_repo,        # Pass the @instance function
    auth_service=auth_service   # Pass the @instance function
)
```

### Migrating `destructors()`
```python
# Old
def cleanup_connection(conn):
    conn.close()

cleanups = destructors(database=cleanup_connection)

# New - Use context managers or explicit cleanup
@injected
def database():
    conn = create_connection()
    try:
        yield conn
    finally:
        conn.close()
```

### Migrating `injecteds()`
```python
# Old
bindings = injecteds(
    processor=Injected.bind(lambda db: Processor(db))
)

# New
bindings = design(
    processor=Injected.bind(lambda db: Processor(db))
)
```

## Benefits of Migration

1. **Unified API**: Single `design()` function for all binding types
2. **Better Tooling**: The linter can better analyze `design()` usage (e.g., PINJ034)
3. **Composability**: Designs can be easily combined with `+` operator
4. **Type Safety**: Better type inference with the modern API
5. **Future Proof**: The deprecated functions will be removed in future versions

## Configuration

This rule can be disabled in your `pyproject.toml`:

```toml
[tool.pinjected-linter]
disable = ["PINJ035"]
```

## Severity

**Error** - These functions are deprecated and will be removed in future versions of pinjected.

## See Also

- [PINJ034: No lambda or non-decorated functions in design()](./pinj034_no_lambda_in_design.md)
- [Pinjected Migration Guide](https://pinjected.readthedocs.io/en/latest/migration/)