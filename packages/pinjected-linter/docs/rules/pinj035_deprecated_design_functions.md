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

# Method 1: Direct design() for simple values
config = design(
    host="localhost",
    port=5432,
    debug=True
)

# Method 2: Using decorators with design()
@injected
def database():
    return DatabaseConnection()

@injected
def logger():
    return Logger()

@instance
def user_service():
    return UserService()

@instance
def auth_service():
    return AuthService()

# Method 3: Using with design() context manager
with design() as d:
    # Add simple values
    d['host'] = 'localhost'
    d['port'] = 5432
    d['debug'] = True
    
    # Add providers
    d.provide(database)
    d.provide(logger)
    d.provide(user_service)
    d.provide(auth_service)

# Method 4: Mixed approach
base_config = design(host="localhost", port=5432)

with design() as services:
    services.provide(database)
    services.provide(logger)

# Combine designs
final_design = base_config + services
```

## Specific Migration Patterns

### Migrating `instances()`
```python
# Old
config = instances(api_key="secret", timeout=30)

# New - Option 1
config = design(api_key="secret", timeout=30)

# New - Option 2
with design() as config:
    config['api_key'] = 'secret'
    config['timeout'] = 30
```

### Migrating `providers()`
```python
# Old
def get_service():
    return Service()

services = providers(service=get_service)

# New - Option 1 (with decorator)
@injected
def service():
    return Service()

with design() as d:
    d.provide(service)

# New - Option 2 (with Injected.bind)
services = design(service=Injected.bind(lambda: Service()))
```

### Migrating `classes()`
```python
# Old
bindings = classes(UserRepo=UserRepository, AuthService=AuthService)

# New - Option 1 (with @instance)
@instance
def user_repo():
    return UserRepository()

@instance
def auth_service():
    return AuthService()

with design() as d:
    d.provide(user_repo)
    d.provide(auth_service)

# New - Option 2 (direct)
bindings = design(
    user_repo=UserRepository(),
    auth_service=AuthService()
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
3. **Context Manager Support**: The `with design()` pattern provides cleaner syntax
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