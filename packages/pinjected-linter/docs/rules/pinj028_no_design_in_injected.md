# PINJ028: No design() Usage Inside @injected Functions

## Overview

This rule forbids using the `design()` context manager inside `@injected` functions. This is a fundamental misuse of pinjected's design pattern.

## Rationale

From the pinjected documentation:

> @injected functions build an AST (computation graph), not executing the functions directly.

The `design()` function is used to configure dependency blueprints **outside** of the execution context. Using `design()` inside an `@injected` function indicates a misunderstanding of the separation between:

1. **Configuration time**: When you use `design()` to set up your dependency graph
2. **Declaration time**: When you define `@injected` functions that declare dependencies
3. **Runtime**: When the actual execution happens

## Examples

### ❌ Incorrect

```python
from pinjected import injected, design

@injected
async def a_test_v3_implementation(
    logger,
    /,
    sketch_path: str
) -> dict:
    # WRONG: design() should not be used inside @injected
    with design() as d:
        @injected
        async def a_tracking_sketch_to_line_art(
            a_auto_cached_sketch_to_line_art,
            /,
            sketch_path: str
        ) -> dict:
            return await a_auto_cached_sketch_to_line_art(sketch_path=sketch_path)
        
        d.provide(a_tracking_sketch_to_line_art)
    
    # This pattern shows confusion about pinjected's architecture
    result = await a_tracking_sketch_to_line_art(sketch_path=sketch_path)
    return result

@injected
def configure_dynamically(config_loader, /, env: str):
    config = config_loader.load(env)
    
    # WRONG: Trying to configure dependencies at runtime
    with design() as d:
        if config.use_mock:
            d.provide(mock_database)
        else:
            d.provide(real_database)
    
    # This doesn't work - design() is for configuration, not runtime
```

### ✅ Correct

```python
from pinjected import injected, design, instance
from typing import Protocol

# Define protocols
class LineArtProtocol(Protocol):
    async def __call__(self, sketch_path: str) -> dict: ...

class DatabaseProtocol(Protocol):
    def query(self, sql: str) -> list: ...

# Define @injected functions at module level
@injected(protocol=LineArtProtocol)
async def a_tracking_sketch_to_line_art(
    a_auto_cached_sketch_to_line_art,
    /,
    sketch_path: str
) -> dict:
    # No await needed when calling injected dependencies!
    return a_auto_cached_sketch_to_line_art(sketch_path=sketch_path)

@injected
async def a_test_v3_implementation(
    a_tracking_sketch_to_line_art: LineArtProtocol,  # Inject as dependency
    logger,
    /,
    sketch_path: str
) -> dict:
    # Call the injected function directly
    result = a_tracking_sketch_to_line_art(sketch_path=sketch_path)
    return result

# Configure dependencies OUTSIDE of @injected functions
def configure_app(use_mock: bool = False):
    with design() as d:
        d.provide(a_tracking_sketch_to_line_art)
        d.provide(a_auto_cached_sketch_to_line_art)
        
        # Configuration decisions happen here, not at runtime
        if use_mock:
            d.provide(mock_database)
        else:
            d.provide(real_database)
    
    return d.to_graph()

# Alternative: Use @instance for conditional dependencies
@instance
def database(config) -> DatabaseProtocol:
    if config.use_mock:
        return MockDatabase()
    else:
        return RealDatabase(config.db_url)
```

## Key Principles

1. **design() is for configuration, not execution**: Use `design()` to set up your dependency graph before runtime, not during it.

2. **@injected functions declare structure**: They define how dependencies connect, not when or how to configure them.

3. **Configuration is static**: Once your dependency graph is built, it doesn't change during execution.

4. **Use @instance for conditional logic**: If you need runtime decisions about which implementation to use, handle that in `@instance` providers.

## Common Misunderstandings

1. **Trying to configure dependencies dynamically**: Pinjected's dependency graph is built once, not reconfigured during execution.

2. **Confusing @injected with regular functions**: @injected functions are dependency declarations, not normal Python functions.

3. **Misunderstanding the execution model**: When you call an @injected function inside another @injected function, you're building a graph, not executing code.

## How to Fix

1. Move all `design()` usage outside of `@injected` functions
2. Configure your dependency graph at application startup
3. Use `@instance` providers for any conditional dependency logic
4. Remember: `design()` is for blueprints, `@injected` is for declarations, execution happens later

## Configuration

This rule can be disabled in your `pyproject.toml`:

```toml
[tool.pinjected-linter]
disable = ["PINJ028"]
```

## Severity

**Error** - Using `design()` inside `@injected` functions violates pinjected's fundamental architecture and will not work as expected.

## See Also

- [PINJ027: No nested @injected functions](./pinj027_no_nested_injected.md)
- [PINJ010: Design usage](./pinj010_design_usage.md)
- [Pinjected Usage Guide - design() Function](https://github.com/pinjected/pinjected/blob/main/docs/how_to_use_pinjected.md)