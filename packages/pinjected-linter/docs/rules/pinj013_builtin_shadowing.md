# PINJ013: Builtin Shadowing

## Overview

**Rule ID:** PINJ013  
**Category:** Naming  
**Severity:** Warning  
**Auto-fixable:** No

Functions decorated with `@instance` or `@injected` should not shadow Python built-in names, as this can cause confusion and unexpected behavior.

## Rationale

Shadowing Python built-in names is problematic because:

1. **Confusion**: Developers expect built-in names to refer to Python's standard types and functions
2. **Unexpected Behavior**: Can lead to subtle bugs when the shadowed name is used elsewhere
3. **Poor Readability**: Makes code harder to understand and maintain
4. **IDE Issues**: Can confuse static analysis tools and IDEs
5. **Future Compatibility**: Python may add new built-ins in future versions

In the context of Pinjected, where dependencies are injected by name, shadowing built-ins can be especially confusing as these names become part of your dependency graph.

## Rule Details

This rule checks function names decorated with `@instance` or `@injected` against Python's built-in names from the `builtins` module.

### Built-ins Checked

Common types:
- `dict`, `list`, `set`, `tuple`, `str`, `int`, `float`, `bool`, `bytes`, `bytearray`
- `object`, `type`, `super`, `property`, `classmethod`, `staticmethod`

Common functions:
- `len`, `range`, `enumerate`, `zip`, `map`, `filter`, `sorted`, `reversed`
- `sum`, `min`, `max`, `abs`, `round`, `pow`, `divmod`
- `all`, `any`, `next`, `iter`

I/O and system:
- `open`, `print`, `input`, `format`, `compile`, `exec`, `eval`
- `id`, `hash`, `hex`, `oct`, `bin`, `chr`, `ord`

And many more from Python's `builtins` module.

### Examples of Violations

❌ **Bad:** Functions that shadow built-in names
```python
from pinjected import instance, injected

@instance
def dict():  # Error: Shadows built-in 'dict'
    return {"config": "value"}

@instance
def list():  # Error: Shadows built-in 'list'
    return [1, 2, 3]

@injected
def open(file_handler, /, filename):  # Error: Shadows built-in 'open'
    return file_handler.open(filename)

@injected
def type(object_inspector, /, obj):  # Error: Shadows built-in 'type'
    return object_inspector.get_type(obj)

# Async functions too
@instance
async def input():  # Error: Shadows built-in 'input'
    return await get_user_input()
```

✅ **Good:** Descriptive names that don't shadow built-ins
```python
from pinjected import instance, injected

@instance
def config_dict():  # Good: Descriptive name
    return {"config": "value"}

@instance
def item_list():  # Good: Specific name
    return [1, 2, 3]

@injected
def open_file(file_handler, /, filename):  # Good: Action-based name
    return file_handler.open(filename)

@injected
def get_object_type(object_inspector, /, obj):  # Good: Clear intent
    return object_inspector.get_type(obj)

@instance
async def user_input():  # Good: Specific name
    return await get_user_input()
```

## Common Patterns and Best Practices

### 1. Use descriptive prefixes or suffixes

Instead of generic built-in names, add context:
```python
# ❌ Bad
@instance
def dict():
    return load_config()

# ✅ Good - Add context
@instance
def config_dict():
    return load_config()

@instance
def settings_dict():
    return load_settings()

@instance
def app_dict():
    return {"name": "MyApp", "version": "1.0"}
```

### 2. Use action-based names for functions

For `@injected` functions, use verbs that describe what they do:
```python
# ❌ Bad
@injected
def filter(data_processor, /, items):
    return data_processor.filter(items)

# ✅ Good - Action-based
@injected
def filter_items(data_processor, /, items):
    return data_processor.filter(items)

@injected
def apply_filter(data_processor, /, items):
    return data_processor.filter(items)
```

### 3. Domain-specific naming

Use names that reflect your domain:
```python
# ❌ Bad
@instance
def type():
    return UserType.ADMIN

# ✅ Good - Domain-specific
@instance
def user_type():
    return UserType.ADMIN

@instance
def account_type():
    return AccountType.PREMIUM
```

### 4. Configuration and factory patterns

When creating configuration or factory functions:
```python
# ❌ Bad
@instance
def vars():
    return {"DEBUG": True}

# ✅ Good
@instance
def env_vars():
    return {"DEBUG": True}

@instance
def config_vars():
    return {"DEBUG": True}
```

## Configuration

This rule has configurable severity:

```toml
[tool.pinjected-linter]
[tool.pinjected-linter.rules.PINJ013]
severity = "warning"  # or "error" for stricter enforcement
```

## When to Disable

You might want to disable this rule if:
- You're working with legacy code that already uses these names
- You have a specific naming convention that conflicts
- You're creating wrapper functions that intentionally mirror built-ins

To disable for a specific function:
```python
@instance
def dict():  # noqa: PINJ013
    # Legacy code - will refactor later
    return get_legacy_config()
```

To disable in configuration:
```toml
[tool.pinjected-linter]
disable = ["PINJ013"]
```

## Migration Guide

When fixing violations:

1. **Add descriptive context**:
   - `dict` → `config_dict`, `settings_dict`, `data_dict`
   - `list` → `item_list`, `user_list`, `result_list`
   - `type` → `object_type`, `user_type`, `data_type`

2. **Use action verbs for @injected**:
   - `filter` → `filter_items`, `apply_filter`
   - `map` → `map_values`, `transform_items`
   - `open` → `open_file`, `open_connection`

3. **Consider the function's purpose**:
   - What does it return? Use that in the name
   - What does it do? Use action words
   - What domain does it belong to? Add domain context

## Related Rules

- **PINJ001:** Instance naming conventions
- **PINJ003:** Async instance naming with `a_` prefix

## See Also

- [Python Built-in Functions](https://docs.python.org/3/library/functions.html)
- [PEP 8 - Naming Conventions](https://www.python.org/dev/peps/pep-0008/#naming-conventions)
- [Pinjected Best Practices](https://pinjected.readthedocs.io/best-practices)

## Version History

- **1.0.0:** Initial implementation