# PINJ009: Injected Async Function Prefix

## Overview

**Rule ID:** PINJ009  
**Category:** Naming  
**Severity:** Error  
**Auto-fixable:** Yes

Async functions decorated with `@injected` must have the `a_` prefix to clearly distinguish them from synchronous functions.

## Rationale

The `a_` prefix convention for async `@injected` functions is crucial for:

1. **Async Boundary Visibility:** Makes it immediately clear which functions are asynchronous
2. **Prevention of Sync/Async Mixing:** Helps prevent accidentally calling async functions from sync context
3. **Consistency:** Follows Pinjected's established naming conventions
4. **Type Safety:** IDEs and type checkers can better infer async behavior
5. **Code Readability:** Developers can quickly identify async dependencies

## Rule Details

This rule ensures that all async functions decorated with `@injected` start with the `a_` prefix. This is the opposite of PINJ003, which prevents `@instance` functions from having the `a_` prefix.

### Examples of Violations

❌ **Bad:** Async @injected functions without a_ prefix
```python
@injected
async def fetch_user(database, /, user_id: str):  # Error: Missing a_ prefix
    return await database.get_user(user_id)

@injected
async def save_data(storage, logger, /, data: dict):  # Error: Missing a_ prefix
    logger.info("Saving data")
    await storage.save(data)

@injected
async def process_batch(processor, /, items: list):  # Error: Missing a_ prefix
    results = []
    for item in items:
        result = await processor.process(item)
        results.append(result)
    return results
```

✅ **Good:** Async @injected functions with a_ prefix
```python
@injected
async def a_fetch_user(database, /, user_id: str):  # Correct: a_ prefix
    return await database.get_user(user_id)

@injected
async def a_save_data(storage, logger, /, data: dict):  # Correct: a_ prefix
    logger.info("Saving data")
    await storage.save(data)

@injected
async def a_process_batch(processor, /, items: list):  # Correct: a_ prefix
    results = []
    for item in items:
        result = await processor.process(item)
        results.append(result)
    return results
```

## Common Patterns and Best Practices

### 1. Consistent async naming throughout the call chain
```python
# ❌ Bad - inconsistent naming
@injected
async def fetch_data(api_client, /, endpoint: str):  # Missing a_ prefix
    return await api_client.get(endpoint)

@injected
async def process_data(fetch_data, transformer, /, endpoint: str):  # Missing a_ prefix
    data = await fetch_data(endpoint)
    return await transformer.transform(data)

# ✅ Good - consistent a_ prefix
@injected
async def a_fetch_data(api_client, /, endpoint: str):
    return await api_client.get(endpoint)

@injected
async def a_process_data(a_fetch_data, a_transformer, /, endpoint: str):
    # Note: No await when calling @injected functions - building AST!
    data = a_fetch_data(endpoint)
    # But DO use await for non-@injected async methods
    return await a_transformer.transform(data)
```

### 2. Mixing sync and async dependencies
```python
# ✅ Good - clear distinction between sync and async
@injected
async def a_create_report(
    logger,           # Sync dependency
    validator,        # Sync dependency
    a_fetch_data,     # Async dependency
    a_send_email,     # Async dependency
    /,
    report_type: str
):
    logger.info(f"Creating {report_type} report")
    
    # Sync operations
    if not validator.is_valid_type(report_type):
        raise ValueError(f"Invalid report type: {report_type}")
    
    # Async operations - No await for @injected functions (building AST)
    data = a_fetch_data(report_type)
    report = generate_report(data)
    a_send_email(report)  # No await - building AST
    
    return report
```

### 3. Async function calling patterns
```python
# ❌ Bad - unclear async boundaries
@injected
async def get_user_data(database, cache, /, user_id: str):
    # Is cache.get async? Is database.fetch async?
    cached = cache.get(user_id)  # Unclear
    if cached:
        return cached
    return await database.fetch(user_id)  # Async

# ✅ Good - clear async boundaries with a_ prefix
@injected
async def a_get_user_data(a_database, cache, /, user_id: str):
    # Clear: cache is sync, a_database is async
    cached = cache.get(user_id)
    if cached:
        return cached
    return await a_database.fetch(user_id)
```

### 4. Async context managers and iterators
```python
# ✅ Good - async operations clearly marked
@injected
async def a_process_stream(
    a_stream_reader,
    processor,
    logger,
    /,
    stream_id: str
):
    logger.info(f"Processing stream {stream_id}")
    
    async with a_stream_reader(stream_id) as stream:
        async for item in stream:
            result = processor.process(item)  # Sync processing
            if result:
                yield result
```

## Auto-fix Behavior

This rule provides automatic fixes that add the `a_` prefix to async `@injected` functions:

```python
# Before auto-fix
@injected
async def fetch_data(...):
    pass

# After auto-fix
@injected
async def a_fetch_data(...):
    pass
```

Note: The auto-fix only changes the function definition. You'll need to manually update all call sites to use the new name.

## Configuration

This rule has no configuration options.

## When to Disable

You should rarely disable this rule as it enforces an important naming convention. Consider disabling only if:
- You're migrating legacy code and need time to update function names
- You're using a different async naming convention consistently

To disable for a specific function:
```python
# noqa: PINJ009
@injected
async def legacy_async_function(database, /):
    # Will be renamed in next refactor
    return await database.query()
```

To disable in configuration:
```toml
[tool.pinjected-linter]
disable = ["PINJ009"]
```

## Relationship with Other Rules

This rule works in conjunction with:
- **PINJ003:** Prevents `@instance` functions from having `a_` prefix (the opposite rule)
- **PINJ015:** Ensures proper slash separator usage in async `@injected` functions

## See Also

- [Python async/await documentation](https://docs.python.org/3/library/asyncio-task.html)
- [Pinjected async patterns](https://pinjected.readthedocs.io/async)

## Version History

- **1.0.0:** Initial implementation with auto-fix support