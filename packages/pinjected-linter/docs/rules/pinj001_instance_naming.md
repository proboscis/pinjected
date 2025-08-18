# PINJ001: Instance Naming

## Overview

**Rule ID:** PINJ001  
**Category:** Naming  
**Severity:** Error  
**Auto-fixable:** Yes

Functions decorated with `@instance` should follow noun-based naming conventions that describe what they provide, not what they do.

## Rationale

The `@instance` decorator is used to define dependency providers in Pinjected. These functions should be named as nouns that describe the resource or service they provide, not as verbs that describe actions. This naming convention:

1. Makes it clear that the function provides a dependency, not performs an action
2. Aligns with dependency injection patterns where you inject "things" not "actions"
3. Improves code readability and maintainability
4. Makes the dependency graph easier to understand

## Rule Details

This rule flags `@instance` functions that:
- Start with common verb prefixes (get_, create_, make_, build_, construct_, initialize_, setup_, fetch_, load_, provide_)
- Use standalone verbs as names (e.g., `connect`, `authenticate`)

### Examples of Violations

❌ **Bad:** Verb-based naming
```python
@instance
def get_database():  # Starts with 'get_'
    return Database()

@instance
def create_client():  # Starts with 'create_'
    return HttpClient()

@instance
def build_cache():  # Starts with 'build_'
    return RedisCache()

@instance
def connect():  # Standalone verb
    return Connection()
```

✅ **Good:** Noun-based naming
```python
@instance
def database():  # What it provides
    return Database()

@instance
def http_client():  # Descriptive noun
    return HttpClient()

@instance
def redis_cache():  # Clear resource name
    return RedisCache()

@instance
def database_connection():  # Noun phrase
    return Connection()
```

## Common Patterns and Best Practices

### 1. Use descriptive nouns
```python
# ❌ Bad
@instance
def get_config():
    return Config()

# ✅ Good
@instance
def configuration():
    return Config()

# ✅ Better - more specific
@instance
def app_configuration():
    return Config()
```

### 2. Use noun phrases for complex dependencies
```python
# ❌ Bad
@instance
def create_user_service():
    return UserService()

# ✅ Good
@instance
def user_service():
    return UserService()

# ✅ Also good - compound noun
@instance
def user_management_service():
    return UserService()
```

### 3. Async instances follow the same rule
```python
# ❌ Bad
@instance
async def create_async_client():
    return await AsyncClient.create()

# ✅ Good
@instance
async def async_client():
    return await AsyncClient.create()
```

## Configuration

This rule has no configuration options.

## When to Disable

You might want to disable this rule if:
- You're working with legacy code that follows different naming conventions
- You have a specific naming standard that conflicts with this rule
- You're in a migration phase from verb-based to noun-based naming

To disable for a specific function:
```python
# noqa: PINJ001
@instance
def get_legacy_service():  # Legacy code, will refactor later
    return LegacyService()
```

To disable in configuration:
```toml
[tool.pinjected-linter]
disable = ["PINJ001"]
```

## Related Rules

- **PINJ002:** Instance function defaults (prevents default arguments in `@instance` functions)
- **PINJ003:** Async instance naming (prevents `a_` prefix on async `@instance` functions)

## Version History

- **1.0.0:** Initial implementation