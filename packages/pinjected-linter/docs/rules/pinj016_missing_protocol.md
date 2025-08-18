# PINJ016: Missing Protocol Parameter in @injected

## Overview

This rule ensures that `@injected` functions specify a Protocol using the `protocol` parameter. According to pinjected best practices, all `@injected` functions should define and use a Protocol for better type safety, IDE support, and maintainability.

Additionally, this rule detects when the protocol parameter is a string literal instead of a proper Protocol class, which is an error.

## Rationale

From the pinjected documentation:

> When implementing `@injected` functions, you should always define a Protocol for the function interface and specify it using the `protocol` parameter. This provides better type safety, IDE support, and makes your code more maintainable.

Using Protocol with `@injected` functions:
- Provides clear interface contracts
- Enables better type checking and IDE autocomplete
- Makes the code more self-documenting
- Helps prevent runtime errors from interface mismatches

## Examples

### ❌ Incorrect

```python
from pinjected import injected

# Missing protocol parameter
@injected
def process_data(logger, /, data: str) -> str:
    logger.info(f"Processing: {data}")
    return data.upper()

# Has other parameters but still missing protocol
@injected(cache=True)
def cached_processor(database, /, query: str) -> list:
    return database.execute(query)

# Async function also needs protocol
@injected
async def a_fetch_data(client, /, url: str) -> dict:
    return await client.get(url)

# String literal protocol is not allowed
@injected(protocol="ProcessorProtocol")  # Error: string literal
def bad_processor(logger, /, data: str) -> str:
    return data

@injected(protocol="ABatchAdd1Protocol")  # Error: string literal
async def a_batch_add_1(items: list[dict]) -> list[dict]:
    return [dict(x=item["x"] + 1) for item in items]
```

### ✅ Correct

```python
from typing import Protocol
from pinjected import injected

# Define the protocol
class ProcessorProtocol(Protocol):
    def __call__(self, data: str) -> str: ...

# Use protocol parameter
@injected(protocol=ProcessorProtocol)
def process_data(logger, /, data: str) -> str:
    logger.info(f"Processing: {data}")
    return data.upper()

# Protocol with other parameters
class QueryProtocol(Protocol):
    def __call__(self, query: str) -> list: ...

@injected(protocol=QueryProtocol, cache=True)
def cached_processor(database, /, query: str) -> list:
    return database.execute(query)

# Async protocol
class AsyncFetcherProtocol(Protocol):
    async def __call__(self, url: str) -> dict: ...

@injected(protocol=AsyncFetcherProtocol)
async def a_fetch_data(client, /, url: str) -> dict:
    return await client.get(url)
```

## How to Fix

1. Define a Protocol class that matches your function's signature (excluding injected dependencies)
2. Add the `protocol` parameter to your `@injected` decorator
3. Pass the Protocol class as the value

Example transformation:
```python
# Before
@injected
def send_email(email_client, /, to: str, subject: str, body: str) -> bool:
    return email_client.send(to, subject, body)

# After
from typing import Protocol

class EmailSenderProtocol(Protocol):
    def __call__(self, to: str, subject: str, body: str) -> bool: ...

@injected(protocol=EmailSenderProtocol)
def send_email(email_client, /, to: str, subject: str, body: str) -> bool:
    return email_client.send(to, subject, body)
```

## Configuration

This rule can be disabled in your `pyproject.toml`:

```toml
[tool.pinjected-linter]
disable = ["PINJ016"]
```

## Severity

- **Warning** - Missing protocol parameter. While not using protocols doesn't break functionality, it misses out on significant type safety and IDE support benefits.
- **Error** - Using string literal as protocol parameter. This is incorrect usage and must be fixed to use a proper Protocol class.

## See Also

- [Pinjected Usage Guide - Protocol Best Practices](https://github.com/pinjected/pinjected/blob/main/docs/how_to_use_pinjected.md#best-practice-always-define-and-use-protocol)
- [PEP 544 - Protocols: Structural subtyping](https://www.python.org/dev/peps/pep-0544/)