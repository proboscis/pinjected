# PINJ044: No Direct AsyncResolver Creation

## Overview

`AsyncResolver` is an internal implementation detail of pinjected and should never be instantiated directly by users. Use the proper pinjected API methods instead.

## Rationale

`AsyncResolver` is a low-level internal class that handles dependency resolution within pinjected. Direct usage of `AsyncResolver`:

1. **Breaks Encapsulation**: Exposes internal implementation details that may change
2. **Bypasses Safety Features**: Skips validation and safety checks built into the public API
3. **Complicates Migration**: Makes code harder to upgrade when pinjected internals change
4. **Missing Features**: Doesn't benefit from high-level features like automatic cleanup, proper error handling, and lifecycle management
5. **API Instability**: Internal classes are not part of the stable API and may change without notice

The pinjected library provides proper high-level APIs that should be used instead.

## Examples

### ❌ Incorrect

```python
from pinjected import AsyncResolver, design

# VIOLATION: Direct AsyncResolver creation
d = design(database="test_db", cache="redis")
resolver = AsyncResolver(d)
result = await resolver.provide("database")

# VIOLATION: Module import style
import pinjected
resolver = pinjected.AsyncResolver(pinjected.design())

# VIOLATION: In class initialization
class ServiceManager:
    def __init__(self):
        self.resolver = AsyncResolver(design())
    
    async def get_service(self, name):
        return await self.resolver.provide(name)

# VIOLATION: Factory function
def create_test_resolver():
    return AsyncResolver(design(test_mode=True))
```

### ✅ Correct

```python
from pinjected import design, injected

# Define your application with @injected decorator
@injected
def my_app(database, cache, logger, /):
    logger.info("Starting application")
    service = ServiceImpl(database, cache)
    return service.run()

# Configure your design
app_design = design(
    database="test_db",
    cache="redis",
    logger=lambda: logging.getLogger(__name__)
)

# Run using the CLI command (not in Python code):
# $ python -m pinjected run my_module.my_app --overrides='{my_module.app_design}'

# For testing: use pytest fixtures
from pinjected.test import register_fixtures_from_design

test_design = design()
test_design.provide(database="test_db")
test_design.provide(cache="test_cache")
register_fixtures_from_design(test_design)

def test_with_fixtures(database, cache):
    # database and cache are injected as pytest fixtures
    assert database == "test_db"
    assert cache == "test_cache"

# For async applications
@injected
async def async_app(database, cache, logger, /):
    logger.info("Starting async application")
    result = await database.query("SELECT * FROM users")
    await cache.set("users", result)
    return result

# Configure design for async app
async_design = design(
    database=async_database,
    cache=async_cache,
    logger=lambda: logging.getLogger(__name__)
)

# Run using CLI command:
# $ python -m pinjected run my_module.async_app --overrides='{my_module.async_design}'
```

## Special Cases

If you absolutely need to use `AsyncResolver` directly (extremely rare), you can mark it with a special comment:

```python
from pinjected import AsyncResolver, design

d = design()
# pinjected: allow-async-resolver
resolver = AsyncResolver(d)  # Allowed with explicit marker
```

Or use the standard noqa comment:

```python
resolver = AsyncResolver(d)  # noqa: PINJ044
```

## Migration Guide

To fix violations of this rule:

1. **For running applications**: Use `pinjected run` command
   ```python
   # Before (in Python code)
   resolver = AsyncResolver(d)
   result = await resolver.provide(my_app)
   
   # After (define app and run via CLI)
   @injected
   def my_app(dependencies, /):
       # app logic here
       return result
   
   # Run via command line:
   # $ python -m pinjected run module.my_app --overrides='{module.my_design}'
   ```

2. **For testing**: Use `register_fixtures_from_design()`
   ```python
   # Before
   resolver = AsyncResolver(test_design)
   service = await resolver.provide("service")
   
   # After
   register_fixtures_from_design(test_design)
   def test_something(service):  # service injected as fixture
       assert service is not None
   ```

3. **For dependency inspection**: Use design inspection methods
   ```python
   # Before
   resolver = AsyncResolver(d)
   keys = resolver.design.keys()
   
   # After
   keys = d.keys()
   ```

## Configuration

```toml
[rules.PINJ044]
enabled = true
severity = "error"
```

## See Also

- [Pinjected Public API Documentation](https://github.com/pinjected/pinjected)
- [PINJ043: No design() in Test Functions](./pinj043_no_design_in_test_functions.md)
- [Pinjected Design Patterns](../../../docs/design-patterns.md)