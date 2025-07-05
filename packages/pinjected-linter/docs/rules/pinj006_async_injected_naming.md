# PINJ006: Async Injected Naming

## Overview

**Rule ID:** PINJ006  
**Category:** Naming  
**Severity:** Error  
**Auto-fixable:** Yes

Async `@injected` functions MUST have `a_` prefix.

## Rationale

The `a_` prefix clearly indicates that a function is async and helps distinguish between sync and async operations in Pinjected's dependency injection system. This is a strong convention in the Pinjected ecosystem that:

1. **Makes async boundaries visible:** Developers can immediately see which functions are asynchronous
2. **Prevents sync/async mixing errors:** Helps avoid accidentally calling async functions from sync contexts
3. **Improves code readability:** Clear visual distinction between sync and async operations
4. **Enables better tooling:** IDEs and type checkers can leverage this convention
5. **Maintains consistency:** Follows established Pinjected naming patterns

## Rule Details

This rule checks that all async functions decorated with `@injected` start with the `a_` prefix. The prefix must be lowercase `a` followed by an underscore.

### Examples of Violations

❌ **Bad:** Async @injected functions without a_ prefix
```python
@injected
async def fetch_data(api_client, /, id):  # ❌ Missing a_ prefix
    return await api_client.get(id)

@injected
async def process_queue(mq, /, message):  # ❌ Missing a_ prefix
    return await mq.process(message)

@injected
async def upload_file(storage, /, file):  # ❌ Missing a_ prefix
    return await storage.upload(file)

# Wrong case
@injected
async def A_fetch_data(api, /):  # ❌ Capital A not allowed
    return await api.get_all()

# a_ in wrong position
@injected
async def fetch_a_data(api, /):  # ❌ a_ must be at start
    return await api.get_data()
```

✅ **Good:** Proper async @injected naming
```python
@injected
async def a_fetch_data(api_client, /, id):  # ✅ Has a_ prefix
    return await api_client.get(id)

@injected
async def a_process_queue(mq, /, message):  # ✅ Has a_ prefix
    return await mq.process(message)

@injected
async def a_upload_file(storage, /, file):  # ✅ Has a_ prefix
    return await storage.upload(file)

# Sync functions don't need a_ prefix
@injected
def fetch_data_sync(api_client, /, id):  # ✅ Sync function
    return api_client.get_sync(id)

# Multiple underscores are OK after a_
@injected
async def a__special_case(api, /):  # ✅ Valid (though unusual)
    return await api.special()

# Complex names work fine
@injected
async def a_fetch_user_profile_with_permissions(api, /, user_id):  # ✅
    return await api.get_user_full(user_id)
```

## Common Patterns and Best Practices

### 1. Sync/Async pairs
```python
# Good practice: Clear distinction between sync and async versions
@injected
def fetch_user(db, /, user_id):
    return db.query_user(user_id)

@injected
async def a_fetch_user(db, /, user_id):
    return await db.query_user_async(user_id)
```

### 2. Async chains
```python
# All async @injected functions in a chain should have a_ prefix
@injected
async def a_fetch_data(api, /, id):
    return await api.get(id)

@injected
async def a_process_data(a_fetch_data, /, id):
    data = a_fetch_data(id)  # Note: No await here (building AST)
    return data.transform()

@injected
async def a_save_results(a_process_data, storage, /, id):
    result = a_process_data(id)
    return storage.save(result)
```

### 3. Mixed async/sync dependencies
```python
@injected
async def a_complex_operation(
    sync_service,     # Sync dependency
    a_fetch_data,     # Async dependency  
    logger,           # Sync dependency
    /,
    request
):
    logger.info("Starting operation")
    data = a_fetch_data(request.id)
    processed = sync_service.process(data)
    return processed
```

## Edge Cases

### Multiple underscores
```python
@injected
async def a__fetch_data(): ...  # ✅ Valid (has a_ prefix)
```

### Capital letters
```python
@injected
async def A_fetch_data(): ...  # ❌ Invalid (wrong case)

@injected
async def a_FetchData(): ...   # ✅ Valid (a_ is lowercase)
```

### Prefix position
```python
@injected
async def fetch_a_data(): ...  # ❌ Invalid (a_ not at start)

@injected
async def _a_private(): ...    # ❌ Invalid (a_ not at start)
```

## Auto-fix Behavior

The rule automatically adds the `a_` prefix to async @injected functions:

- `fetch_data` → `a_fetch_data`
- `processQueue` → `a_processQueue`
- `UPLOAD_FILE` → `a_UPLOAD_FILE`

The fix preserves the original name's casing and simply prepends `a_`.

## Configuration

This rule has no configuration options. The `a_` prefix requirement is mandatory for all async @injected functions.

## When to Disable

This rule should rarely be disabled as it enforces a core Pinjected convention. Only disable when:
- Migrating legacy code gradually
- Integrating with third-party code that doesn't follow this convention

To disable for a specific function:
```python
# noqa: PINJ006
@injected
async def legacy_async_function(api, /):
    return await api.call()
```

To disable in configuration:
```toml
[tool.pinjected-linter]
disable = ["PINJ006"]
```

## Related Rules

- **PINJ003:** Prevents @instance functions from having a_ prefix
- **PINJ005:** Injected function naming convention (verb forms)
- **PINJ009:** No await in injected AST building

## See Also

- [Pinjected Documentation - Async Functions](https://pinjected.readthedocs.io/async)
- [Python Async/Await](https://docs.python.org/3/library/asyncio-task.html)

## Version History

- **1.0.0:** Initial implementation matching Linear issue ARC-289