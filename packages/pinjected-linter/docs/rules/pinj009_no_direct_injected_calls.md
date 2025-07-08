# PINJ009: No Direct Calls to @injected Functions

## Overview

Inside `@injected` functions, you're building a dependency graph (AST), not executing code. Direct calls to other `@injected` functions are fundamentally wrong - they should be declared as dependencies and injected, not called directly.

This rule detects and prevents direct calls or await expressions on `@injected` functions within other `@injected` functions.

## Rationale

The `@injected` decorator is part of Pinjected's dependency injection system. When you write an `@injected` function, you're not writing code that executes immediately - you're defining a node in a dependency graph that will be resolved later.

Key principles:
1. **Dependencies must be declared** - If an `@injected` function needs another `@injected` function, it must be declared as a dependency (before the `/`)
2. **No execution inside @injected** - You should not execute or await other `@injected` functions
3. **Build the graph, don't run it** - The actual execution happens when the dependency graph is resolved

## Examples

### ❌ Incorrect

```python
from pinjected import injected

@injected
def process_data(/, data: str) -> str:
    return data.upper()

@injected
def analyze_results(/, results):
    # ERROR: Direct call to @injected function
    processed = process_data(results)  
    return processed

@injected
async def a_fetch_data(/, url: str) -> dict:
    return {"data": "example"}

@injected
async def a_process_all(/, urls: list):
    # ERROR: Await call to @injected function
    data = await a_fetch_data(urls[0])
    return data
```

### ✅ Correct

```python
from pinjected import injected

@injected
def process_data(/, data: str) -> str:
    return data.upper()

@injected
def analyze_results(process_data, /, results):
    # CORRECT: process_data is declared as a dependency
    return process_data(results)

@injected
async def a_fetch_data(/, url: str) -> dict:
    return {"data": "example"}

@injected
async def a_process_all(a_fetch_data, /, urls: list):
    # CORRECT: a_fetch_data is declared as a dependency
    # Note: Don't await it - return the coroutine/future
    return a_fetch_data(urls[0])
```

## Common Mistakes

### Mistake 1: Forgetting to declare dependencies

```python
# Wrong
@injected
def handler(/, data):
    result = validator(data)  # ERROR: validator not declared
    return processor(result)  # ERROR: processor not declared

# Correct
@injected
def handler(validator, processor, /, data):
    result = validator(data)
    return processor(result)
```

### Mistake 2: Using await inside @injected

```python
# Wrong
@injected
async def a_handler(/, data):
    result = await a_validator(data)  # ERROR: Don't await
    return result

# Correct
@injected
async def a_handler(a_validator, /, data):
    return a_validator(data)  # Return the coroutine
```

### Mistake 3: Mixing regular and @injected functions

```python
def regular_helper(data):
    return data.lower()

@injected
def process(/, data):
    # OK: regular_helper is not @injected
    lower = regular_helper(data)
    
    # ERROR: other_injected is @injected
    result = other_injected(lower)
    return result
```

## Suppressing with noqa

In rare cases where you need to suppress this rule (e.g., during migration), you can use `# noqa`:

```python
@injected
def legacy_handler(/, data):
    # Direct call with explanation
    result = process_data(data)  # noqa: PINJ009 - Migrating legacy code
    return result
```

**Important**: Always provide a reason when using `noqa` to suppress this error.

## Configuration

This rule cannot be disabled as it catches a fundamental misuse of the `@injected` decorator.

## Severity

**Error** - This is always an error because it represents a fundamental misunderstanding of how dependency injection works in Pinjected.

## See Also

- [Pinjected Documentation - Dependency Injection](https://github.com/pinjected/pinjected)
- PINJ015: Missing slash separator in @injected functions