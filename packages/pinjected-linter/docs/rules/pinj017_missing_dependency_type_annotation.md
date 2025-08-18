# PINJ017: Missing Type Annotation for Dependencies

## Overview

This rule ensures that dependencies in `@instance` and `@injected` functions have type annotations. Type annotations on dependencies improve code clarity, enable better IDE support, and help catch type-related bugs early.

## Rationale

Type annotations for dependencies provide several benefits:

1. **Type Safety**: Catch type mismatches at development time rather than runtime
2. **IDE Support**: Better autocomplete, refactoring, and navigation
3. **Documentation**: Clear interface contracts for dependencies
4. **Maintainability**: Easier to understand what types of objects are expected

For `@instance` functions, all parameters are dependencies that should be typed.
For `@injected` functions, parameters before the `/` separator are dependencies that should be typed.

## Examples

### ❌ Incorrect

```python
from pinjected import instance, injected

# @instance without type annotations
@instance
def database(host, port):
    return Database(host, port)

# @instance with partial annotations
@instance
def cache(host: str, port, ttl):
    return Cache(host, port, ttl)

# @injected without type annotations for dependencies
@injected
def process_data(logger, database, /, data: str) -> str:
    logger.info(f"Processing {data}")
    return database.query(data)

# @injected with partial annotations
@injected
def fetch_data(client: HttpClient, cache, /, url: str) -> dict:
    if data := cache.get(url):
        return data
    return client.get(url)
```

### ✅ Correct

```python
from pinjected import instance, injected
from typing import Protocol

# @instance with type annotations
@instance
def database(host: str, port: int) -> Database:
    return Database(host, port)

@instance
def cache(host: str, port: int, ttl: int) -> Cache:
    return Cache(host, port, ttl)

# Define protocols for dependencies
class LoggerProtocol(Protocol):
    def info(self, msg: str) -> None: ...

class DatabaseProtocol(Protocol):
    def query(self, q: str) -> str: ...

# @injected with type annotations for all dependencies
@injected
def process_data(logger: LoggerProtocol, database: DatabaseProtocol, /, data: str) -> str:
    logger.info(f"Processing {data}")
    return database.query(data)

class CacheProtocol(Protocol):
    def get(self, key: str) -> dict | None: ...

@injected
def fetch_data(client: HttpClient, cache: CacheProtocol, /, url: str) -> dict:
    if data := cache.get(url):
        return data
    return client.get(url)
```

## How to Fix

1. Add type annotations to all dependency parameters
2. For complex types, consider using Protocol classes
3. Import necessary types from `typing` module

Example transformation:
```python
# Before
@instance
def logger(level, format):
    return Logger(level, format)

# After
@instance
def logger(level: str, format: str) -> Logger:
    return Logger(level, format)
```

For `@injected` functions:
```python
# Before
@injected
def send_email(email_client, logger, /, to: str, subject: str) -> bool:
    logger.info(f"Sending email to {to}")
    return email_client.send(to, subject)

# After
from typing import Protocol

class EmailClientProtocol(Protocol):
    def send(self, to: str, subject: str) -> bool: ...

class LoggerProtocol(Protocol):
    def info(self, msg: str) -> None: ...

@injected
def send_email(
    email_client: EmailClientProtocol,
    logger: LoggerProtocol,
    /,
    to: str,
    subject: str
) -> bool:
    logger.info(f"Sending email to {to}")
    return email_client.send(to, subject)
```

## Configuration

This rule can be disabled in your `pyproject.toml`:

```toml
[tool.pinjected-linter]
disable = ["PINJ017"]
```

## Severity

**Warning** - Missing type annotations don't break functionality but miss out on significant type safety and development experience benefits.

## See Also

- [PEP 484 - Type Hints](https://www.python.org/dev/peps/pep-0484/)
- [PEP 544 - Protocols: Structural subtyping](https://www.python.org/dev/peps/pep-0544/)
- [Python Type Checking Guide](https://docs.python.org/3/library/typing.html)