# PINJ005: Instance Function Imports

## Overview

**Rule ID:** PINJ005  
**Category:** Imports  
**Severity:** Error  
**Auto-fixable:** No

Functions decorated with `@instance` should not contain import statements. All imports should be at module level.

## Rationale

Placing imports inside `@instance` functions violates several important principles:

1. **Performance:** Imports are executed every time the function is called
2. **Predictability:** Import errors occur at runtime rather than module load time
3. **Clarity:** Dependencies are hidden inside functions rather than declared at the top
4. **Testing:** Makes it harder to mock or patch imports
5. **Best Practices:** Violates PEP 8 guidelines for import placement

## Rule Details

This rule flags any `import` or `from ... import` statements inside `@instance` decorated functions.

### Examples of Violations

❌ **Bad:** Imports inside @instance functions
```python
@instance
def database():
    import sqlite3  # Error: Import inside @instance
    return sqlite3.connect(":memory:")

@instance
def redis_client():
    from redis import Redis  # Error: Import inside @instance
    return Redis(host='localhost')

@instance
def logger():
    import logging  # Error: Import inside @instance
    import sys      # Error: Multiple imports
    
    handler = logging.StreamHandler(sys.stdout)
    return logging.getLogger(__name__)

@instance
async def async_client():
    import aiohttp  # Error: Also applies to async @instance
    return aiohttp.ClientSession()
```

✅ **Good:** Module-level imports
```python
import sqlite3
from redis import Redis
import logging
import sys
import aiohttp

@instance
def database():
    return sqlite3.connect(":memory:")

@instance
def redis_client():
    return Redis(host='localhost')

@instance
def logger():
    handler = logging.StreamHandler(sys.stdout)
    return logging.getLogger(__name__)

@instance
async def async_client():
    return aiohttp.ClientSession()
```

## Common Patterns and Best Practices

### 1. Move all imports to the top
```python
# ❌ Bad - conditional imports
@instance
def get_driver():
    if config.database_type == "postgres":
        import psycopg2
        return psycopg2.connect(...)
    else:
        import sqlite3
        return sqlite3.connect(...)

# ✅ Good - import both at module level
import psycopg2
import sqlite3

@instance
def get_driver():
    if config.database_type == "postgres":
        return psycopg2.connect(...)
    else:
        return sqlite3.connect(...)
```

### 2. Handle optional dependencies
```python
# ❌ Bad - lazy import for optional dependency
@instance
def cache():
    try:
        import redis
        return redis.Redis()
    except ImportError:
        return MemoryCache()

# ✅ Good - handle at module level
try:
    import redis
    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False

@instance
def cache():
    if HAS_REDIS:
        return redis.Redis()
    else:
        return MemoryCache()
```

### 3. Avoid circular imports properly
```python
# ❌ Bad - using function-level import to avoid circular import
@instance
def user_service():
    from .models import User  # Avoiding circular import
    return UserService(User)

# ✅ Good - restructure to avoid circular imports
# Or use TYPE_CHECKING for type hints only
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import User

@instance
def user_service():
    # Import the actual module properly
    from . import models
    return UserService(models.User)
```

## Why This Matters

1. **Startup Failures:** Module-level imports fail fast at startup, function-level imports fail at runtime
2. **Performance Impact:** Imports have overhead, especially for large modules
3. **Debugging:** Stack traces are clearer when imports are at module level
4. **Static Analysis:** Tools can better analyze dependencies with module-level imports

## Configuration

This rule has no configuration options.

## When to Disable

This rule should rarely be disabled. The only valid cases might be:
- Working with legacy code during migration
- Very specific dynamic import requirements

To disable for a specific function:
```python
# noqa: PINJ005
@instance
def legacy_provider():
    import legacy_module  # Will fix in next refactor
    return legacy_module.Provider()
```

To disable in configuration:
```toml
[tool.pinjected-linter]
disable = ["PINJ005"]
```

## Related Rules

- **PINJ006:** Instance function side effects (imports could be considered side effects)

## See Also

- [PEP 8 - Imports](https://www.python.org/dev/peps/pep-0008/#imports)
- [Python Import System](https://docs.python.org/3/reference/import.html)

## Version History

- **1.0.0:** Initial implementation