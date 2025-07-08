# PINJ018: Don't Call injected() on Already @injected Functions

## Overview

This rule detects when `injected()` is called on a function that is already decorated with `@injected`. This is redundant and incorrect - the `@injected` decorator already wraps the function with the necessary injection logic.

## Rationale

When a function is decorated with `@injected`, it's already been transformed into an injectable component. Calling `injected()` on it again:

1. **Is redundant** - The function is already wrapped
2. **May cause unexpected behavior** - Double wrapping can lead to confusion
3. **Indicates a misunderstanding** - Shows the developer doesn't understand that `@injected` already does the wrapping

The correct pattern is to use the decorated function directly with its methods like `.proxy()`, `.bind()`, etc.

## Examples

### ❌ Incorrect

```python
from pinjected import injected

@injected
def a_user_registration_workflow(
    create_user_fn,
    logger,
    /,
    user_data: list[dict]
) -> None:
    for data in user_data:
        create_user_fn(
            user_id=data["id"],
            name=data["name"],
            email_address=data["email"]
        )

# ERROR: a_user_registration_workflow is already @injected
test_workflow = injected(a_user_registration_workflow).proxy(
    user_data=[
        {"id": "1", "name": "Alice", "email": "alice@example.com"},
    ]
).bind(
    create_user_fn=a_create_user
)
```

### ✅ Correct

```python
from pinjected import injected

@injected
def a_user_registration_workflow(
    create_user_fn,
    logger,
    /,
    user_data: list[dict]
) -> None:
    for data in user_data:
        create_user_fn(
            user_id=data["id"],
            name=data["name"],
            email_address=data["email"]
        )

# CORRECT: Use the decorated function directly
test_workflow = a_user_registration_workflow.proxy(
    user_data=[
        {"id": "1", "name": "Alice", "email": "alice@example.com"},
    ]
).bind(
    create_user_fn=a_create_user
)
```

## Common Patterns

### Pattern 1: Using injected() as a function

```python
# For undecorated functions, injected() is used as a function
def regular_function(dep1, /, arg1):
    return dep1.process(arg1)

# CORRECT: regular_function is not decorated
wrapped = injected(regular_function)
```

### Pattern 2: Using @injected as a decorator

```python
# When using as decorator, the function is already wrapped
@injected
def decorated_function(dep1, /, arg1):
    return dep1.process(arg1)

# CORRECT: Use directly
result = decorated_function.proxy(arg1="value")
```

## Migration Guide

If you have code that calls `injected()` on already decorated functions:

```python
# Before (incorrect)
@injected
def my_function(...): ...

result = injected(my_function).proxy(...)

# After (correct)
@injected
def my_function(...): ...

result = my_function.proxy(...)
```

Simply remove the `injected()` call and use the function directly.

## Suppressing with noqa

In rare cases where you need to suppress this rule, you can use `# noqa`:

```python
# Only if absolutely necessary during migration
result = injected(already_decorated).proxy(...)  # noqa: PINJ018 - Legacy code migration
```

## Severity

**Error** - This is always an error because it indicates incorrect usage of the dependency injection system.

## See Also

- [Pinjected Documentation - @injected decorator](https://github.com/pinjected/pinjected)
- PINJ009: No direct calls to @injected functions