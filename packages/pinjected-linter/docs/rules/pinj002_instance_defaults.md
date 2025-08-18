# PINJ002: Instance Function Default Arguments

## Overview

**Rule ID:** PINJ002  
**Category:** Design  
**Severity:** Error  
**Auto-fixable:** No

Functions decorated with `@instance` should not have default arguments. Configuration should be provided through the `design()` function instead.

## Rationale

The `@instance` decorator marks functions as dependency providers. While they can accept parameters, they should not have default values for those parameters. This design principle ensures:

1. Consistent behavior across all dependency instantiations
2. No runtime configuration of dependencies (configuration should be injected)
3. Clear separation between dependency providers and regular functions
4. Prevention of hidden state or configuration

## Rule Details

This rule flags any `@instance` function that has parameters with default values.

### Examples of Violations

❌ **Bad:** Instance functions with default arguments
```python
@instance
def database(host="localhost"):  # Default parameter
    return Database(host=host)

@instance
def cache(ttl=3600):  # Default parameter
    return Cache(ttl=ttl)

@instance
def logger(level="INFO", format=None):  # Multiple defaults
    return Logger(level=level, format=format)

@instance
async def async_client(timeout=30):  # Async with default
    return AsyncClient(timeout=timeout)
```

✅ **Good:** Instance functions without default arguments
```python
@instance
def database():
    # Configuration is hardcoded or injected through other means
    return Database(host="localhost")

@instance
def cache():
    # TTL is set internally or through configuration
    return Cache(ttl=3600)

@instance
def logger():
    # Logger configuration is handled internally
    return Logger(level="INFO", format=None)

@instance
async def async_client():
    # Timeout is configured internally
    return AsyncClient(timeout=30)
```

## Common Patterns and Best Practices

### 1. Use configuration objects for parameterization
```python
# ❌ Bad - using defaults
@instance
def database(host="localhost", port=5432):
    return Database(host=host, port=port)

# ✅ Good - use design() for configuration
@instance
def database(host, port):
    return Database(host=host, port=port)

# Configure via design
base_design = design(
    host="localhost",
    port=5432
)
```

### 2. Create multiple instances for variations
```python
# ❌ Bad - parameterized instance
@instance
def cache(name="default"):
    return Cache(name=name)

# ✅ Good - specific instances
@instance
def default_cache():
    return Cache(name="default")

@instance
def user_cache():
    return Cache(name="users")

@instance
def session_cache():
    return Cache(name="sessions")
```

### 3. Use environment variables or config files
```python
# ❌ Bad - runtime configuration
@instance
def api_client(base_url="https://api.example.com"):
    return APIClient(base_url=base_url)

# ✅ Good - environment-based configuration
@instance
def api_client():
    import os
    base_url = os.environ.get("API_BASE_URL", "https://api.example.com")
    return APIClient(base_url=base_url)
```

## Configuration

This rule has no configuration options.

## When to Disable

You might want to disable this rule if:
- You're migrating from a different dependency injection system
- You have legacy code that uses parameterized providers
- You're using a custom pattern that requires default parameters

To disable for a specific function:
```python
# noqa: PINJ002
@instance
def legacy_service(config=None):  # Legacy pattern
    return LegacyService(config or default_config)
```

To disable in configuration:
```toml
[tool.pinjected-linter]
disable = ["PINJ002"]
```

## Related Rules

- **PINJ001:** Instance naming (ensures proper naming conventions)

## See Also

- [Pinjected documentation on @instance decorator](https://pinjected.readthedocs.io/instance)
- [Pinjected design() function documentation](https://pinjected.readthedocs.io/design)

## Version History

- **1.0.0:** Initial implementation