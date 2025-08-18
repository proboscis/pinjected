# PINJ003: Async Instance Naming

## Overview

**Rule ID:** PINJ003  
**Category:** Naming  
**Severity:** Error  
**Auto-fixable:** Yes

Async functions decorated with `@instance` should not have the `a_` prefix. Pinjected handles async resolution automatically.

## Rationale

In Pinjected, the `@instance` decorator handles both sync and async dependency providers transparently. The framework automatically manages async resolution, so there's no need to signal async behavior through naming conventions. This rule ensures:

1. Consistent naming for all `@instance` functions regardless of sync/async
2. Focus on what the dependency provides, not its implementation details
3. Cleaner dependency names in the injection system
4. Prevention of confusion with `@injected` functions (which do use `a_` prefix for async)

## Rule Details

This rule flags async `@instance` functions that start with the `a_` prefix.

### Examples of Violations

❌ **Bad:** Async instance functions with `a_` prefix
```python
@instance
async def a_database():  # Don't use a_ prefix
    conn = await create_connection()
    return Database(conn)

@instance
async def a_redis_client():  # Don't use a_ prefix
    client = await Redis.create()
    return client

@instance
async def a_message_queue():  # Don't use a_ prefix
    return await MessageQueue.connect()
```

✅ **Good:** Async instance functions without prefix
```python
@instance
async def database():  # No prefix needed
    conn = await create_connection()
    return Database(conn)

@instance
async def redis_client():  # Clean name
    client = await Redis.create()
    return client

@instance
async def message_queue():  # Focus on what it provides
    return await MessageQueue.connect()
```

## Common Patterns and Best Practices

### 1. Name by what it provides, not how
```python
# ❌ Bad - implementation detail in name
@instance
async def a_async_database():
    return await Database.create_async()

# ✅ Good - just the resource name
@instance
async def database():
    return await Database.create_async()
```

### 2. Consistency between sync and async
```python
# ✅ Good - consistent naming regardless of implementation
@instance
def cache():  # Sync version
    return InMemoryCache()

@instance
async def cache():  # Async version - same name
    return await RedisCache.create()
```

### 3. This is different from @injected functions
```python
# @instance - NO prefix for async
@instance
async def database():
    return await Database.create()

# @injected - YES prefix for async
@injected
async def a_fetch_user(database, /, user_id: str):
    return await database.get_user(user_id)
```

## Why This Matters

Pinjected's dependency resolution system handles async dependencies automatically:

```python
# Both sync and async instances are used the same way
@injected
def user_service(database, cache, /):  # Works with both sync/async instances
    # Pinjected handles async resolution internally
    return UserService(database, cache)
```

The consumer doesn't need to know if the dependency is async - Pinjected manages that complexity.

## Configuration

This rule has no configuration options.

## When to Disable

You might want to disable this rule if:
- You have a company-wide convention that requires `a_` prefix for all async functions
- You're migrating from another system that uses this convention
- You need to maintain compatibility with existing code

To disable for a specific function:
```python
# noqa: PINJ003
@instance
async def a_legacy_service():  # Keeping for compatibility
    return await LegacyService.create()
```

To disable in configuration:
```toml
[tool.pinjected-linter]
disable = ["PINJ003"]
```

## Related Rules

- **PINJ001:** Instance naming (general naming conventions for @instance)
- **PINJ009:** Injected async prefix (requires `a_` prefix for async @injected functions)

## Key Differences

| Decorator | Async Prefix | Example |
|-----------|--------------|---------|
| `@instance` | No `a_` prefix | `async def database():` |
| `@injected` | Yes `a_` prefix | `async def a_fetch_user(...):` |

## Version History

- **1.0.0:** Initial implementation