# PINJ049: Enforce Protocol Type Annotations for Dependencies

## Overview

This rule ensures that when `@injected` or `@instance` functions have a `protocol=T` annotation, any dependencies that use these functions should have type annotation `T` instead of generic types like `Callable`, `Any`, or `object`.

## Rationale

When a function is annotated with `protocol=T`, it explicitly declares its interface contract through the protocol type `T`. Using generic types like `Callable`, `Any`, or `object` for such dependencies:

1. **Loses Type Safety**: The specific protocol interface is not enforced
2. **Reduces IDE Support**: No autocomplete or type checking for protocol methods
3. **Obscures Intent**: The actual expected interface is hidden
4. **Breaks Liskov Substitution**: Generic types don't guarantee protocol compliance

## Examples

### ❌ Incorrect

```python
from pinjected import injected, instance
from typing import Callable, Any, Protocol

class DatabaseProtocol(Protocol):
    def query(self, sql: str) -> list: ...

@injected(protocol=DatabaseProtocol)
def database(config, /, host: str) -> DatabaseProtocol:
    return SQLDatabase(config, host)

# Using Callable instead of DatabaseProtocol
@injected
def process_data(database: Callable, /, data: str) -> str:
    # Type checker can't verify this is correct
    return database().query(data)

# Using Any instead of the protocol
@injected
def analyze_data(database: Any, /, query: str) -> list:
    # No type safety at all
    return database.query(query)

# Instance with protocol using object type
class CacheProtocol(Protocol):
    def get(self, key: str) -> Any: ...
    def set(self, key: str, value: Any) -> None: ...

@instance(protocol=CacheProtocol)
def redis_cache(host: str, port: int) -> CacheProtocol:
    return RedisCache(host, port)

@injected
def fetch_data(redis_cache: object, /, key: str) -> Any:
    # No type checking for cache methods
    return redis_cache.get(key)
```

### ✅ Correct

```python
from pinjected import injected, instance
from typing import Protocol

class DatabaseProtocol(Protocol):
    def query(self, sql: str) -> list: ...

@injected(protocol=DatabaseProtocol)
def database(config, /, host: str) -> DatabaseProtocol:
    return SQLDatabase(config, host)

# Using the specific protocol type
@injected
def process_data(database: DatabaseProtocol, /, data: str) -> str:
    # Type checker can verify query() method exists
    return database.query(data)[0]

@injected
def analyze_data(database: DatabaseProtocol, /, query: str) -> list:
    # Full type safety and IDE support
    return database.query(query)

# Instance with protocol
class CacheProtocol(Protocol):
    def get(self, key: str) -> Any: ...
    def set(self, key: str, value: Any) -> None: ...

@instance(protocol=CacheProtocol)
def redis_cache(host: str, port: int) -> CacheProtocol:
    return RedisCache(host, port)

@injected
def fetch_data(redis_cache: CacheProtocol, /, key: str) -> Any:
    # Type checking ensures get() method exists
    return redis_cache.get(key)
```

## Auto-fix Support

This rule supports automatic fixing. The linter will:

1. Detect dependencies using generic types (`Callable`, `Any`, `object`)
2. Look up the corresponding protocol type from the function's `protocol=T` annotation
3. Replace the generic type with the specific protocol type

Example auto-fix:
```python
# Before
@injected
def service(database: Any, cache: Callable, /, request: Request) -> Response:
    ...

# After auto-fix
@injected
def service(database: DatabaseProtocol, cache: CacheProtocol, /, request: Request) -> Response:
    ...
```

## How to Fix

1. Identify all functions with `protocol=T` annotations
2. Find dependencies that use these functions
3. Replace generic type annotations with the specific protocol types

Manual fix example:
```python
# Step 1: Identify the protocol
@injected(protocol=LoggerProtocol)
def logger(level: str) -> LoggerProtocol:
    return Logger(level)

# Step 2: Find usage with generic type
@injected
def process(logger: Any, /, data: str) -> None:  # Wrong!
    logger.info(data)

# Step 3: Replace with protocol type
@injected
def process(logger: LoggerProtocol, /, data: str) -> None:  # Correct!
    logger.info(data)
```

## Configuration

This rule can be disabled in your `pyproject.toml`:

```toml
[tool.pinjected-linter]
disable = ["PINJ049"]
```

## Severity

**Warning** - Using generic types instead of specific protocols reduces type safety but doesn't break functionality.

## See Also

- [PINJ016: Missing Protocol](pinj016_missing_protocol.md) - Ensures `@injected` functions have protocol annotations
- [PINJ017: Missing Dependency Type Annotation](pinj017_missing_dependency_type_annotation.md) - Ensures dependencies have type annotations
- [PINJ026: a_ Prefix Dependency Any Type](pinj026_a_prefix_dependency_any_type.md) - Specific rule for async dependencies
- [PEP 544 - Protocols: Structural subtyping](https://www.python.org/dev/peps/pep-0544/)