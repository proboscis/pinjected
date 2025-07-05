# PINJ009: No Await in Injected AST Building

## Overview

**Rule ID:** PINJ009  
**Category:** Injection  
**Severity:** Error  
**Auto-fixable:** No

Don't use `await` when calling `@injected` functions inside other `@injected` functions.

## Rationale

Inside `@injected` functions, you're building an Abstract Syntax Tree (AST), not executing code directly. Using `await` on calls to other `@injected` functions is incorrect because:

1. **AST Building vs Execution:** `@injected` functions construct a dependency graph, they don't execute immediately
2. **Deferred Execution:** The actual execution happens later when the dependency graph is resolved
3. **Type Mismatch:** Awaiting an AST node construction doesn't make sense and will cause runtime errors
4. **Conceptual Error:** It indicates a misunderstanding of how Pinjected's dependency injection works

## Rule Details

This rule detects when `await` is used on calls to other `@injected` functions within an `@injected` function body. The rule understands that inside `@injected` functions, calls to other `@injected` functions are building the AST, not executing the functions.

### Examples of Violations

❌ **Bad:** Using await on @injected function calls
```python
@injected
async def a_fetch_data(api, /, user_id):
    return await api.get_user(user_id)

@injected
async def a_process_user(logger, /, user):
    logger.info(f"Processing {user}")
    return user.process()

# Bad - Should trigger PINJ009
@injected
async def a_bad_example(a_fetch_data, a_process_user, /, user_id):
    # These awaits are WRONG - building AST, not executing!
    data = await a_fetch_data(user_id)  # ❌ No await in AST!
    result = await a_process_user(data)  # ❌ No await in AST!
    return result

# More bad examples
@injected
async def a_another_bad(a_fetch_data, logger, /, ids):
    results = []
    for id in ids:
        # This await is wrong!
        data = await a_fetch_data(id)  # ❌ No await!
        results.append(data)
    return results

@injected
async def a_complex_bad(a_fetch_data, a_process_user, cache, /, user_id):
    # Multiple incorrect awaits
    if user_id in cache:
        return cache[user_id]
    
    data = await a_fetch_data(user_id)  # ❌ Wrong!
    processed = await a_process_user(data)  # ❌ Wrong!
    cache[user_id] = processed
    return processed
```

✅ **Good:** No await when calling @injected functions
```python
@injected
async def a_good_example(a_fetch_data, a_process_user, /, user_id):
    # Correct - no await when calling @injected functions
    data = a_fetch_data(user_id)  # ✅ Building AST
    result = a_process_user(data)  # ✅ Building AST
    return result

# Also good - await on non-@injected calls
@injected
async def a_mixed_example(api_client, a_process_data, /, url):
    # This await is OK - api_client is not @injected
    raw_data = await api_client.fetch(url)  # ✅ OK to await
    # But this should not have await
    processed = a_process_data(raw_data)  # ✅ No await
    return processed

@injected
async def a_correct_loop(a_transform, db, /, ids):
    # Await on actual async operations is fine
    results = []
    for id in ids:
        record = await db.fetch_record(id)  # ✅ db is not @injected
        transformed = a_transform(record)  # ✅ No await on @injected
        results.append(transformed)
    return results
```

## Common Patterns and Best Practices

### 1. Understanding AST Building
```python
@injected
async def a_user_workflow(a_fetch_user, a_validate_user, a_save_user, /, user_id):
    # This builds an AST that represents:
    # 1. Call a_fetch_user with user_id
    # 2. Pass result to a_validate_user
    # 3. Pass that result to a_save_user
    user = a_fetch_user(user_id)  # No await - AST node
    validated = a_validate_user(user)  # No await - AST node
    saved = a_save_user(validated)  # No await - AST node
    return saved
```

### 2. Mixing injected and non-injected calls
```python
@injected
async def a_hybrid_function(a_process, logger, db, /, data):
    # logger and db are regular dependencies (not @injected functions)
    logger.info("Starting process")
    
    # OK to await non-injected async methods
    existing = await db.find_existing(data.id)  # ✅ await is OK
    
    if existing:
        return existing
    
    # No await on @injected function calls
    result = a_process(data)  # ✅ No await
    
    # OK to await non-injected async methods
    await db.save(result)  # ✅ await is OK
    
    return result
```

### 3. Conditional AST building
```python
@injected
async def a_conditional_flow(a_process_a, a_process_b, config, /, data):
    # Building different ASTs based on config
    if config.use_process_a:
        # No await - building AST
        return a_process_a(data)  # ✅
    else:
        # No await - building AST
        return a_process_b(data)  # ✅
```

## Why This Matters

### Conceptual Understanding
```python
# When you write this:
@injected
async def a_workflow(a_step1, a_step2, /, data):
    result1 = a_step1(data)
    result2 = a_step2(result1)
    return result2

# Pinjected builds an AST like:
# workflow = lambda data: a_step2(a_step1(data))

# The actual execution happens later when called through the container
```

### Runtime Errors
```python
# This will fail at runtime:
@injected
async def a_broken(a_fetch, /, id):
    data = await a_fetch(id)  # ❌ TypeError: can't await AST node
    return data
```

## Common Misconceptions

### "But my function is async!"
Being async doesn't mean you should await @injected calls:
```python
@injected
async def a_function(a_helper, real_async_service, /, data):
    # Await real async operations
    prepared = await real_async_service.prepare(data)  # ✅
    
    # Don't await @injected function calls
    result = a_helper(prepared)  # ✅ No await
    
    # Await real async operations
    await real_async_service.cleanup()  # ✅
    
    return result
```

## Configuration

This rule has no configuration options.

## When to Disable

This rule should never be disabled as violating it will cause runtime errors. If you think you need to disable it, you likely misunderstand how Pinjected works.

## Related Rules

- **PINJ008:** Injected dependency declaration
- **PINJ006:** Async injected naming (a_ prefix)
- **PINJ015:** Missing slash in @injected functions

## See Also

- [Pinjected Documentation - Understanding AST Building](https://pinjected.readthedocs.io/ast-building)
- [Pinjected Documentation - @injected decorator](https://pinjected.readthedocs.io/injected)
- [Python AsyncIO](https://docs.python.org/3/library/asyncio.html)

## Version History

- **1.0.0:** Initial implementation matching Linear issue ARC-294