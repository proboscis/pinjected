# PINJ010: Design() Usage Patterns

## Overview

**Rule ID:** PINJ010  
**Category:** Usage  
**Severity:** Warning  
**Auto-fixable:** No

Ensures proper usage of the `Design()` class for dependency configuration in Pinjected.

## Rationale

The `Design()` class (and its convenience function `design()`) is the primary way to configure and override dependencies in Pinjected. Proper usage ensures:

1. **Clear Configuration:** Dependencies are properly mapped to their providers
2. **Avoid Common Mistakes:** Prevents calling providers instead of referencing them
3. **Proper Composition:** Ensures designs are combined correctly
4. **Meaningful Configurations:** Avoids empty or misconfigured designs
5. **Type Safety:** Maintains proper dependency resolution

## Rule Details

This rule checks for several common misuse patterns:
1. Empty Design() instantiation
2. Using decorator names as keys instead of dependency names
3. Calling @instance functions instead of referencing them
4. Incorrect combination patterns

### Examples of Violations

❌ **Bad:** Common Design() misuse patterns
```python
from pinjected import Design, instance

# Error: Empty Design - no configuration provided
empty_design = Design()

# Error: Using decorator name as key
wrong_key = Design(
    instance=database_provider  # Wrong: 'instance' is not a dependency name
)

# Error: Calling @instance function instead of referencing
@instance
def database_provider():
    return Database()

called_design = Design(
    database=database_provider()  # Wrong: Calling the function
)

# Error: Mixing Design with non-Design objects
mixed = Design(db=database) + {"cache": cache}  # Can't mix types
```

✅ **Good:** Proper Design() usage
```python
from pinjected import Design, design, instance

# Good: Providing configuration
configured_design = Design(
    database=database_provider,      # Reference, not call
    logger=logger_instance,          # Reference, not call
    config=lambda: {"debug": True}   # Lambda is fine
)

# Good: Using the design() convenience function
simple_design = design(
    database=database_provider,
    cache=cache_provider,
    logger=lambda: Logger("myapp")
)

# Good: Combining designs properly
combined = Design(database=db1) + Design(cache=cache1)

# Good: Non-empty with meaningful configuration
app_design = Design(
    database=postgres_provider,
    cache=redis_provider,
    auth_service=auth_provider,
    config=config_provider
)
```

## Common Patterns and Best Practices

### 1. Reference providers, don't call them
```python
# ❌ Bad - calling providers
@instance
def database():
    return PostgresDB()

@instance
def cache():
    return RedisCache()

bad_design = Design(
    db=database(),    # Error: Calling the function
    cache=cache()     # Error: Calling the function
)

# ✅ Good - referencing providers
good_design = Design(
    db=database,      # Reference only
    cache=cache       # Reference only
)

# Also good with design() function
good_design2 = design(
    db=database,
    cache=cache
)
```

### 2. Use dependency names as keys
```python
# ❌ Bad - using decorator or type names
wrong_design = Design(
    instance=database_provider,      # 'instance' is not a dependency
    provider=cache_provider,         # 'provider' is not a dependency
    injected=service_provider        # 'injected' is not a dependency
)

# ✅ Good - using actual dependency names
correct_design = Design(
    database=database_provider,      # 'database' is the dependency name
    cache=cache_provider,            # 'cache' is the dependency name
    user_service=service_provider    # 'user_service' is the dependency name
)
```

### 3. Combine designs properly
```python
# ❌ Bad - incorrect combination
base_design = Design(database=db_provider)
bad_combined = base_design + {"cache": cache_provider}  # Can't add dict

# ✅ Good - proper design combination
base_design = Design(database=db_provider)
cache_design = Design(cache=cache_provider)
good_combined = base_design + cache_design

# Also good - chaining
all_designs = (
    Design(database=db_provider) +
    Design(cache=cache_provider) +
    Design(logger=logger_provider)
)
```

### 4. Use lambdas for simple values
```python
# ✅ Good - lambdas for configuration values
config_design = Design(
    debug_mode=lambda: True,
    max_connections=lambda: 100,
    api_key=lambda: os.environ.get("API_KEY"),
    features=lambda: {"feature_x": True, "feature_y": False}
)

# Also good - mixing providers and lambdas
mixed_design = Design(
    database=database_provider,      # Provider function
    config=lambda: load_config(),    # Lambda
    debug=lambda: True               # Simple value via lambda
)
```

### 5. Environment-specific designs
```python
# ✅ Good - different designs for different environments
def create_app_design(env: str):
    base = Design(
        logger=logger_provider,
        auth=auth_provider
    )
    
    if env == "production":
        return base + Design(
            database=postgres_provider,
            cache=redis_provider,
            monitoring=datadog_provider
        )
    else:
        return base + Design(
            database=sqlite_provider,
            cache=memory_cache_provider,
            monitoring=lambda: None  # No monitoring in dev
        )
```

## Design() vs design()

Pinjected provides both:
- `Design()`: The class for creating design objects
- `design()`: A convenience function that creates a Design instance

Both are valid and the linter accepts either:
```python
# Using Design class
class_design = Design(
    database=db_provider,
    cache=cache_provider
)

# Using design function (convenience)
func_design = design(
    database=db_provider,
    cache=cache_provider
)

# Both are equivalent
```

## Configuration

This rule has no configuration options.

## When to Disable

This rule should rarely be disabled. Consider disabling only if:
- You're using a very specific design pattern that conflicts with the rule
- You're in a migration phase with legacy code

To disable for a specific line:
```python
# noqa: PINJ010
empty_design = Design()  # Will be configured later
```

To disable in configuration:
```toml
[tool.pinjected-linter]
disable = ["PINJ010"]
```

## Related Rules

- **PINJ004:** Direct instance call (related to not calling providers)
- **PINJ008:** Injected dependency declaration (proper dependency usage)

## See Also

- [Pinjected Design documentation](https://pinjected.readthedocs.io/design)
- [Dependency Configuration Patterns](https://pinjected.readthedocs.io/patterns)

## Version History

- **1.0.0:** Initial implementation