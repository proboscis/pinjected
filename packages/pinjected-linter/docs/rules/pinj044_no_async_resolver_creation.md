# PINJ044: No Direct AsyncResolver Creation

## Overview

Direct instantiation of `AsyncResolver` is not allowed. Use the CLI approach (`python -m pinjected run`) for running pinjected applications instead.

## Rationale

Direct usage of `AsyncResolver` is not allowed because:

1. **Configuration Flexibility**: CLI execution allows easy parameter overrides without code changes
2. **Code Volume**: Direct usage increases boilerplate code
3. **Design Philosophy**: Goes against pinjected's principle of separating configuration from execution
4. **Limited Features**: Misses out on CLI features like parameter overrides, design switching, and dependency visualization
5. **Maintenance**: Direct usage couples your code to internal implementation details

The CLI approach provides a cleaner, more flexible, and maintainable solution.

## Examples

### ❌ Incorrect

```python
from pinjected import AsyncResolver, design, instance, IProxy

# VIOLATION: Direct AsyncResolver in __main__ block
if __name__ == "__main__":
    d = design(db_path="./data.db")
    resolver = AsyncResolver(d)  # Error without explicit marking
    
    service = resolver.provide(my_service)
    print(service)

# VIOLATION: AsyncResolver in regular functions
def get_database():
    d = design(database="test_db")
    resolver = AsyncResolver(d)
    return resolver.provide("database")

# VIOLATION: AsyncResolver as class attribute
class ServiceManager:
    def __init__(self):
        self.resolver = AsyncResolver(design())
    
    async def get_service(self, name):
        return await self.resolver.provide(name)

# VIOLATION: Factory functions creating resolvers
def create_resolver(config):
    return AsyncResolver(design(**config))
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

test_design = design(
    database="test_db",
    cache="test_cache"
)
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

If you absolutely need to use `AsyncResolver` directly (extremely rare), you must explicitly mark it with a special comment:

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