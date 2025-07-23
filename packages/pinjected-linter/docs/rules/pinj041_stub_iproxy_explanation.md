# PINJ041: Explain IProxy Transformations in Stub Files

## Overview

This rule validates that `.pyi` stub files correctly show IProxy transformations for `@instance` and `@injected` functions, and provides educational explanations about WHY these transformations happen.

## Purpose

Many developers don't understand why:
- `@instance` functions that return `T` in `.py` files are typed as `IProxy[T]` in `.pyi` files
- `@injected` functions that return `T` should still return `T` in `.pyi` files (not `IProxy[T]`)

This rule helps educate users about pinjected's type transformation behavior while ensuring stub files are correct.

## Rationale

### Understanding @instance Transformation

When you write:
```python
@instance
def database() -> Database:
    return PostgresDatabase()
```

The `@instance` decorator transforms this into a dependency provider. Instead of eagerly executing the function, pinjected:
1. Wraps the function as a lazy proxy
2. Returns `IProxy[Database]` when accessed
3. Resolves dependencies only when the actual value is needed

Therefore, the stub file should reflect what users actually get: `database: IProxy[Database]`

### Understanding @injected Transformation

When you write:
```python
@injected
def process(service, /, data: str) -> dict:
    return service.process(data)
```

The `@injected` decorator:
1. Transforms the function into `IProxy[Callable[[str], dict]]`
2. The function itself becomes a proxy
3. But when called with runtime args, it returns `dict` (not `IProxy[dict]`)

Therefore, the stub file shows the callable's signature: `def process(data: str) -> dict`

## Examples

### ❌ Incorrect Stub Files

#### Wrong @instance Declaration
```python
# module.py
@instance
def database() -> Database:
    return PostgresDatabase()

# module.pyi - WRONG
def database() -> Database: ...  # Should be: database: IProxy[Database]
```

#### Missing IProxy for @instance
```python
# module.py
@instance
def config() -> dict[str, Any]:
    return load_config()

# module.pyi - WRONG
config: dict[str, Any]  # Should be: config: IProxy[dict[str, Any]]
```

#### Wrong @injected Return Type
```python
# module.py
@injected
def fetch_user(db, /, user_id: str) -> User:
    return db.get_user(user_id)

# module.pyi - WRONG
@overload
def fetch_user(user_id: str) -> IProxy[User]: ...  # Should be: -> User
```

#### Missing @overload for @injected
```python
# module.py
@injected
def process(service, /, data: str) -> Result:
    return service.process(data)

# module.pyi - WRONG
def process(data: str) -> Result: ...  # Missing @overload decorator
```

### ✅ Correct Stub Files

```python
# module.py
from pinjected import instance, injected

@instance
def database() -> Database:
    return PostgresDatabase()

@instance
async def cache() -> Cache:
    return await create_cache()

@injected
def fetch_user(db, /, user_id: str) -> User:
    return db.get_user(user_id)

@injected
async def a_process_data(processor, /, data: dict) -> dict:
    return await processor.process(data)

# module.pyi
from typing import overload
from pinjected.di.iproxy import IProxy

# @instance functions become IProxy variables
database: IProxy[Database]
cache: IProxy[Cache]

# @injected functions use @overload with original return types
@overload
def fetch_user(user_id: str) -> User: ...

@overload
async def a_process_data(data: dict) -> dict: ...
```

## Error Messages

This rule provides educational error messages that explain the transformations:

### For @instance Functions

> "@instance function 'database' should be typed as 'database: IProxy[Database]' in the .pyi file.
>
> Why? The @instance decorator transforms your function into a dependency provider. Instead of eagerly executing the function, pinjected wraps it as IProxy[Database] to enable lazy evaluation and dependency injection at runtime. When you access this attribute, pinjected will resolve all dependencies and return the actual Database instance."

### For @injected Functions

> "@injected function 'fetch_user' should NOT have IProxy in its return type in the .pyi file. It should return 'User' directly.
>
> Why? While the @injected decorator makes the function itself an IProxy[Callable[[args], User]], the stub file shows the signature from the user's perspective. When they call the function with runtime arguments, they get back User, not IProxy[User]. The IProxy wrapping happens at the function level, not the return value level."

## Common Mistakes

### Mistake 1: Treating @instance like Regular Functions
```python
# Wrong thinking: "It's a function, so declare it as a function"
def my_instance() -> Service: ...

# Correct: It becomes a lazy proxy variable
my_instance: IProxy[Service]
```

### Mistake 2: Double-wrapping @injected Returns
```python
# Wrong thinking: "Everything needs IProxy"
@overload
def my_func(arg: str) -> IProxy[Result]: ...

# Correct: Users get Result directly when calling
@overload  
def my_func(arg: str) -> Result: ...
```

### Mistake 3: Forgetting @overload
```python
# Wrong: Missing decorator
def my_func(arg: str) -> Result: ...

# Correct: Always use @overload for @injected
@overload
def my_func(arg: str) -> Result: ...
```

## Best Practices

1. **Always check both files**: This rule reads the `.py` file to understand decorators and compares with the `.pyi` file

2. **Remember the perspective**: Stub files show the user-facing interface
   - `@instance`: Users see `IProxy[T]` variables
   - `@injected`: Users call functions and get `T` back

3. **Use the right imports**:
   ```python
   from typing import overload  # For @injected functions
   from pinjected.di.iproxy import IProxy  # For @instance typing
   ```

4. **Keep stub files in sync**: Update `.pyi` files whenever you change decorator usage

## Configuration

This rule has no configuration options. It always validates correct IProxy usage in stub files.

## Severity

**Error** - Incorrect stub files break type checking and IDE support

## See Also

- PINJ014: Missing stub file (generates stub files)
- PINJ032: No IProxy return type in .py files 
- PINJ036: Enforce .pyi stubs for all modules
- [Pinjected Documentation: Creating .pyi Stub Files](https://github.com/pinjected/pinjected#stub-files)