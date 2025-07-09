# PINJ027: No Nested @injected Functions

## Overview

This rule forbids defining `@injected` functions inside other `@injected` functions. This is a fundamental violation of how pinjected works.

## Rationale

From the pinjected documentation:

> @injected functions build an AST (computation graph), not executing the functions directly.

When you define an `@injected` function, you're not executing code - you're building a dependency graph. Defining an `@injected` function inside another `@injected` function doesn't make sense because:

1. The outer `@injected` function builds a computation graph, it doesn't execute code
2. The inner `@injected` definition would be part of the graph structure, not a callable function
3. This violates the separation between dependency declaration and execution

## Examples

### ❌ Incorrect

```python
from pinjected import injected

@injected
def outer_function(database, /, user_id: str):
    # This is wrong - you're trying to define a function in a computation graph
    @injected
    def inner_processor(logger, /, data: dict):
        logger.info(f"Processing: {data}")
        return process(data)
    
    user = database.get_user(user_id)
    return inner_processor(user.data)

@injected
async def a_test_v3_implementation(
    design,  # This is also wrong - design should not be a dependency
    logger,
    /,
    sketch_path: str
) -> dict:
    # Nested @injected function - FORBIDDEN
    @injected
    async def a_tracking_sketch_to_line_art(
        a_auto_cached_sketch_to_line_art: Any,
        /,
        sketch_path: str
    ) -> dict:
        return await a_auto_cached_sketch_to_line_art(sketch_path=sketch_path)
    
    # This pattern indicates misunderstanding of pinjected's design
    result = await a_tracking_sketch_to_line_art(sketch_path=sketch_path)
    return result
```

### ✅ Correct

```python
from pinjected import injected, design
from typing import Protocol

# Define protocols for clarity
class ProcessorProtocol(Protocol):
    def __call__(self, data: dict) -> dict: ...

class TrackingLineArtProtocol(Protocol):
    async def __call__(self, sketch_path: str) -> dict: ...

# Define each @injected function at module level
@injected(protocol=ProcessorProtocol)
def inner_processor(logger, /, data: dict) -> dict:
    logger.info(f"Processing: {data}")
    return process(data)

@injected(protocol=TrackingLineArtProtocol)
async def a_tracking_sketch_to_line_art(
    a_auto_cached_sketch_to_line_art,
    /,
    sketch_path: str
) -> dict:
    return await a_auto_cached_sketch_to_line_art(sketch_path=sketch_path)

# Use dependency injection properly
@injected
def outer_function(
    database,
    inner_processor: ProcessorProtocol,  # Inject as dependency
    /,
    user_id: str
):
    user = database.get_user(user_id)
    return inner_processor(user.data)

@injected
async def a_test_v3_implementation(
    a_tracking_sketch_to_line_art: TrackingLineArtProtocol,  # Inject properly
    logger,
    /,
    sketch_path: str
) -> dict:
    # Call the injected dependency - no await needed!
    result = a_tracking_sketch_to_line_art(sketch_path=sketch_path)
    return result

# Configure dependencies outside of @injected functions
with design() as d:
    d.provide(a_tracking_sketch_to_line_art)
    d.provide(a_auto_cached_sketch_to_line_art)
```

## Key Principles

1. **@injected functions are declarations, not implementations**: When you write an `@injected` function, you're declaring how dependencies connect, not writing executable code.

2. **All @injected functions must be defined at module level**: They are part of your application's dependency structure, not runtime logic.

3. **Dependencies are injected, not created**: If you need another `@injected` function's functionality, inject it as a dependency.

4. **No await for @injected calls inside @injected**: Inside an `@injected` function, calling another `@injected` function doesn't execute it - it builds the graph.

## How to Fix

1. Move all `@injected` function definitions to module level
2. If you need the functionality of another `@injected` function, inject it as a dependency
3. Remember: you're building a dependency graph, not writing procedural code

## Configuration

This rule can be disabled in your `pyproject.toml`:

```toml
[tool.pinjected-linter]
disable = ["PINJ027"]
```

## Severity

**Error** - This is a fundamental violation of pinjected's design principles and will not work as expected.

## See Also

- [PINJ028: No design() usage inside @injected functions](./pinj028_no_design_in_injected.md)
- [Pinjected Usage Guide - Building Dependency Graphs](https://github.com/pinjected/pinjected/blob/main/docs/how_to_use_pinjected.md)