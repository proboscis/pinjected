# PINJ010: design() Usage Patterns

## Overview

**Rule ID:** PINJ010  
**Category:** Usage  
**Severity:** Warning  
**Auto-fixable:** No

Ensures proper usage of the `design()` function for dependency configuration in Pinjected.

## Rationale

The `design()` function is the primary way to configure and override dependencies in Pinjected. Proper usage ensures:

1. **Clear Configuration:** Dependencies are properly mapped to their providers
2. **Avoid Common Mistakes:** Prevents calling providers instead of referencing them
3. **Proper Composition:** Ensures designs are combined correctly
4. **Meaningful Configurations:** Avoids empty or misconfigured designs
5. **Type Safety:** Maintains proper dependency resolution

## Rule Details

This rule checks for several common misuse patterns:
1. Using decorator names as keys instead of dependency names
2. Calling @instance functions instead of referencing them (only detects actual @instance decorated functions)
3. Incorrect combination patterns

Note: The rule tracks @instance decorated functions in your code and only flags calls to those specific functions. Other function calls (like `Injected.pure()`) are allowed.

### Examples of Violations

❌ **Bad:** Common design() misuse patterns
```python
from pinjected import design, instance

# Error: Using decorator name as key
wrong_key = design(
    instance=database  # Wrong: 'instance' is not a dependency name
)

# Error: Calling @instance function instead of referencing
@instance
def database_provider():
    return Database()

called_design = design(
    database=database_provider()  # Wrong: Calling the function
)

# Error: Mixing design with non-design objects
mixed = design(db=database) + {"cache": cache}  # Can't mix types
```

✅ **Good:** Proper design() usage
```python
from pinjected import design, instance

# Good: Empty design is allowed - useful as a base
base_design = design()

# Good: Providing configuration with values and references
configured_design = design(
    database=database,           # Reference, not call
    logger=logger,               # Reference, not call
    batch_size=128,              # Simple value
    learning_rate=0.001          # Simple value
)

# Good: Using the design() function
simple_design = design(
    database=database,
    cache=cache,
    model=model
)

# Good: Combining designs properly
combined = base_design + design(database=db) + design(cache=cache)

# Good: Non-empty with meaningful configuration
app_design = design(
    database=postgres_db,
    cache=redis_cache,
    auth_service=auth,
    config=config
)

# Good: Using Injected factory methods
advanced_design = design(
    pure_value=Injected.pure("test_value"),  # Factory methods are allowed
    by_name=Injected.by_name("some_key"),    # These create IProxy objects
    database=database                         # Reference to @instance function
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

bad_design = design(
    db=database(),    # Error: Calling the function
    cache=cache()     # Error: Calling the function
)

# ✅ Good - referencing providers
good_design = design(
    db=database,      # Reference only
    cache=cache       # Reference only
)
```

### 2. Use dependency names as keys
```python
# ❌ Bad - using decorator or type names
wrong_design = design(
    instance=database_provider,      # 'instance' is not a dependency
    provider=cache_provider,         # 'provider' is not a dependency
    injected=service_provider        # 'injected' is not a dependency
)

# ✅ Good - using actual dependency names
correct_design = design(
    database=database_provider,      # 'database' is the dependency name
    cache=cache_provider,            # 'cache' is the dependency name
    user_service=service_provider    # 'user_service' is the dependency name
)
```

### 3. Combine designs properly
```python
# ❌ Bad - incorrect combination
base_design = design(database=db_provider)
bad_combined = base_design + {"cache": cache_provider}  # Can't add dict

# ✅ Good - proper design combination
base_design = design(database=db_provider)
cache_design = design(cache=cache_provider)
good_combined = base_design + cache_design

# Also good - chaining
all_designs = (
    design(database=db_provider) +
    design(cache=cache_provider) +
    design(logger=logger_provider)
)
```

### 4. Use simple values and references
```python
# ✅ Good - simple values and references
config_design = design(
    debug_mode=True,                 # Simple boolean value
    max_connections=100,             # Simple numeric value
    api_key="sk-1234",              # Simple string value
    features={"feature_x": True}     # Simple dict value
)

# Also good - mixing providers and values
mixed_design = design(
    database=database_provider,      # Provider function reference
    cache=cache_provider,            # Provider function reference
    batch_size=64,                   # Simple value
    learning_rate=0.001              # Simple value
)
```

### 5. Environment-specific designs
```python
# ✅ Good - different designs for different environments
def create_app_design(env: str):
    base = design(
        logger=logger_provider,
        auth=auth_provider
    )
    
    if env == "production":
        return base + design(
            database=postgres_provider,
            cache=redis_provider,
            monitoring=datadog_provider
        )
    else:
        return base + design(
            database=sqlite_provider,
            cache=memory_cache_provider,
            monitoring=null_monitoring_provider  # No monitoring in dev
        )
```

## Using the design() Function

Pinjected provides the `design()` function as the standard way to create dependency configurations:

```python
# Empty design is valid - useful as a base
base_design = design()

# Create a design with the design() function
my_design = design(
    database=database,
    cache=cache,
    logger=logger
)

# Designs can be composed using the + operator
extended_design = base_design + design(database=database) + design(cache=cache)
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
empty_design = design()  # Will be configured later
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