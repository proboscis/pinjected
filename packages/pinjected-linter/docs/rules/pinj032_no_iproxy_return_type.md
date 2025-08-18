# PINJ032: @injected/@instance Functions Should Not Have IProxy Return Type

## Overview

Functions decorated with `@injected` or `@instance` should not have `IProxy` as their return type annotation. This indicates a misunderstanding of how pinjected works. These functions should have ordinary return type annotations.

## Rationale

`IProxy` is an internal interface used by pinjected's dependency injection system. It represents a lazy proxy to a dependency that hasn't been resolved yet. 

Key concepts:

1. **@injected/@instance functions return actual values** - Not proxies
2. **IProxy is internal** - It's used by pinjected internally, not by user code
3. **Use concrete types** - Your functions should return the actual types they produce

When you write:
```python
@injected
def get_service() -> IProxy:  # WRONG!
    return ServiceImpl()
```

You're misunderstanding the role of these decorators. The function returns a `ServiceImpl`, not an `IProxy`.

## Examples

### ❌ Incorrect

```python
from pinjected import injected, instance, IProxy

@injected
def get_service() -> IProxy:
    # ERROR: Should not return IProxy
    return ServiceImpl()

@instance
def database() -> IProxy[Database]:
    # ERROR: Should not return IProxy[T]
    return PostgresDatabase()

@injected
async def async_handler() -> IProxy:
    # ERROR: Async functions also shouldn't return IProxy
    return AsyncHandlerImpl()

# Using module prefix
import pinjected

@pinjected.injected
def processor() -> pinjected.IProxy:
    # ERROR: Still wrong with module prefix
    return ProcessorImpl()
```

### ✅ Correct

```python
from pinjected import injected, instance

@injected
def get_service() -> ServiceInterface:
    # CORRECT: Return the actual interface/class
    return ServiceImpl()

@instance
def database() -> Database:
    # CORRECT: Return the concrete type
    return PostgresDatabase()

@injected
async def async_handler() -> AsyncHandler:
    # CORRECT: Async functions use normal types too
    return AsyncHandlerImpl()

@instance
def config() -> dict[str, Any]:
    # CORRECT: Any type annotation (except IProxy) is fine
    return {"key": "value"}

# No annotation is also OK
@injected
def service():
    # OK: Type inference will work
    return ServiceImpl()
```

## Common Mistakes

### Mistake 1: Confusing IProxy with the actual type

```python
# Wrong - thinking IProxy is needed for DI
@injected
def handler() -> IProxy[Handler]:
    return HandlerImpl()

# Correct - just use the type
@injected
def handler() -> Handler:
    return HandlerImpl()
```

### Mistake 2: Using IProxy in Union types

```python
# Wrong
@injected
def maybe_service() -> IProxy | None:
    if condition:
        return ServiceImpl()
    return None

# Correct
@injected
def maybe_service() -> Service | None:
    if condition:
        return ServiceImpl()
    return None
```

### Mistake 3: Type aliases hiding IProxy

```python
# Problematic type alias
ServiceType = IProxy  # Don't do this!

# Wrong
@instance
def service() -> ServiceType:
    return ServiceImpl()

# Correct
@instance
def service() -> Service:
    return ServiceImpl()
```

## Understanding IProxy

`IProxy` is used internally by pinjected to:
1. Delay dependency resolution
2. Handle circular dependencies
3. Provide lazy initialization

You never need to annotate your functions with `IProxy` because:
- Your functions return actual instances
- Pinjected wraps them in IProxy internally when needed
- The IProxy unwrapping happens automatically

## Migration Guide

If you're coming from another DI framework:

```python
# Old pattern (wrong for pinjected)
@injected
def service() -> IProxy:
    return ServiceImpl()

# New pattern (correct)
@injected
def service() -> ServiceInterface:
    return ServiceImpl()

# Or let type inference work
@injected
def service():
    return ServiceImpl()
```

## Best Practices

1. **Use concrete types or protocols**:
   ```python
   @instance
   def database() -> DatabaseProtocol:
       return PostgresDatabase()
   ```

2. **Use type inference when obvious**:
   ```python
   @injected
   def simple_service():
       return Service()  # Type is clear from return
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
def legacy_service() -> IProxy:  # noqa: PINJ032 - Legacy annotation
    return ServiceImpl()
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
- PINJ031: No calls to injected() inside @instance/@injected functions