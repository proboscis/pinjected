# PINJ033: @injected/@instance Functions Should Not Have IProxy Argument Type Annotations

## Overview

Function arguments in `@injected` or `@instance` decorated functions should not have `IProxy` as their type annotation. This indicates a misunderstanding of how pinjected works. These function arguments should have ordinary type annotations.

## Rationale

`IProxy` is an internal interface used by pinjected's dependency injection system. It represents a lazy proxy to a dependency that hasn't been resolved yet. 

Key concepts:

1. **Dependencies are resolved automatically** - Pinjected handles the resolution
2. **IProxy is internal** - It's used by pinjected internally, not by user code
3. **Use concrete types** - Your function arguments should have the actual types they expect

When you write:
```python
@injected
def service(db: IProxy[Database], logger,/):  # WRONG!
    # db is actually a Database, not an IProxy
    return ServiceImpl(db, logger)
```

You're misunderstanding the role of these decorators. The argument `db` receives a `Database`, not an `IProxy`.

## Examples

### ❌ Incorrect

```python
from pinjected import injected, instance, IProxy

@injected
def get_service(db: IProxy[Database], logger,/):
    # ERROR: Arguments should not be typed as IProxy
    return ServiceImpl(db, logger)

@instance
def api_client(config: IProxy,/):
    # ERROR: Should not use IProxy for argument types
    return APIClient(config)

@injected
async def async_handler(cache: IProxy[Cache], db: IProxy,/):
    # ERROR: Async functions also shouldn't have IProxy argument types
    return AsyncHandlerImpl(cache, db)

# Using module prefix
import pinjected

@pinjected.injected
def processor(queue: pinjected.IProxy,/):
    # ERROR: Still wrong with module prefix
    return ProcessorImpl(queue)

# Multiple arguments with mixed types
@injected
def complex_service(
    db: IProxy[Database],      # ERROR
    cache: Cache,              # OK
    config: IProxy,            # ERROR
    logger,                    # OK (no annotation)
    /
):
    return ComplexService(db, cache, config, logger)
```

### ✅ Correct

```python
from pinjected import injected, instance

@injected
def get_service(db: Database, logger,/):
    # CORRECT: Use the actual interface/class
    return ServiceImpl(db, logger)

@instance
def api_client(config: dict[str, Any],/):
    # CORRECT: Use the concrete type
    return APIClient(config)

@injected
async def async_handler(cache: Cache, db: Database,/):
    # CORRECT: Async functions use normal types too
    return AsyncHandlerImpl(cache, db)

@instance
def factory(settings: Settings, logger: Logger,/):
    # CORRECT: All arguments have proper types
    return Factory(settings, logger)

# No annotation is also OK
@injected
def service(db, logger,/):
    # OK: Type inference will work
    return ServiceImpl(db, logger)
```

## Common Mistakes

### Mistake 1: Confusing IProxy with the actual type

```python
# Wrong - thinking IProxy is needed for DI
@injected
def handler(service: IProxy[Service], config: IProxy,/):
    return HandlerImpl(service, config)

# Correct - just use the types
@injected
def handler(service: Service, config: Config,/):
    return HandlerImpl(service, config)
```

### Mistake 2: Using IProxy in Union types for arguments

```python
# Wrong
@injected
def maybe_service(db: IProxy[Database] | None, logger,/):
    if db:
        return ServiceImpl(db, logger)
    return None

# Correct
@injected
def maybe_service(db: Database | None, logger,/):
    if db:
        return ServiceImpl(db, logger)
    return None
```

### Mistake 3: Type aliases hiding IProxy

```python
# Problematic type alias
DatabaseProxy = IProxy[Database]  # Don't do this!

# Wrong
@instance
def service(db: DatabaseProxy, logger,/):
    return ServiceImpl(db, logger)

# Correct
@instance
def service(db: Database, logger,/):
    return ServiceImpl(db, logger)
```

## Understanding Dependency Injection in Pinjected

When you use `@injected` or `@instance`, pinjected:
1. Analyzes the function signature
2. Resolves dependencies based on parameter names
3. Calls your function with actual instances (not proxies)

You never need to annotate arguments with `IProxy` because:
- Your functions receive actual instances
- Pinjected handles all the proxy management internally
- The IProxy wrapping/unwrapping happens automatically

## Special Case: Self Parameter

In class methods, the `self` parameter is exempt from this rule:

```python
class ServiceFactory:
    @instance
    def create_service(self, db: Database, logger,/):
        # OK: self is exempt, other args properly typed
        return Service(db, logger)
```

## Migration Guide

If you're coming from another DI framework:

```python
# Old pattern (wrong for pinjected)
@injected
def service(db: IProxy[Database], cache: IProxy,/):
    return ServiceImpl(db, cache)

# New pattern (correct)
@injected
def service(db: Database, cache: Cache,/):
    return ServiceImpl(db, cache)

# Or let type inference work
@injected
def service(db, cache,/):
    return ServiceImpl(db, cache)
```

## Best Practices

1. **Use concrete types or protocols**:
   ```python
   @instance
   def service(db: DatabaseProtocol, logger: Logger,/):
       return Service(db, logger)
   ```

2. **Use type inference when obvious**:
   ```python
   @injected
   def simple_service(db, logger,/):
       return Service(db, logger)  # Types are clear from usage
   ```

3. **Never import IProxy in user code**:
   ```python
   # Don't do this
   from pinjected import IProxy
   
   # Do this instead
   from pinjected import injected, instance
   ```

## Suppressing with noqa

This error should rarely be suppressed, but if necessary:

```python
@injected
def legacy_service(db: IProxy[Database], logger,/):  # noqa: PINJ033 - Legacy annotation
    return ServiceImpl(db, logger)
```

**Important**: Fix these annotations as soon as possible. They indicate a misunderstanding that could lead to other issues.

## Configuration

This rule cannot be disabled as it catches incorrect type annotations that could confuse other developers.

## Severity

**Error** - This is an error because it indicates a fundamental misunderstanding of pinjected's type system.

## Further Reading

To understand how pinjected works correctly, please read:
- [Pinjected Documentation](https://github.com/pinjected/pinjected)
- [Understanding Dependency Injection in Pinjected](https://github.com/pinjected/pinjected#concepts)

## See Also

- PINJ011: IProxy annotations (for correct IProxy usage)
- PINJ032: No IProxy return type for @injected/@instance functions
- PINJ015: Missing slash separator in function arguments