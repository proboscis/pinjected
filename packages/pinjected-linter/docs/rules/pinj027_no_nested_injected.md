# PINJ027: No Nested @injected or @instance Definitions

## Overview

This rule forbids defining `@injected` or `@instance` functions inside any function or class. These decorators must only be used at module level.

## Rationale

From the pinjected documentation:

> @injected functions build an AST (computation graph), not executing the functions directly.

`@injected` and `@instance` decorators are used to declare dependencies at the module level. They cannot be defined inside functions or classes because:

1. **Dependency Graph Building**: These decorators build a static dependency graph at module import time, not during runtime execution
2. **Scope Violation**: Defining them inside functions/classes would make them dynamically scoped, violating the static nature of dependency injection
3. **Module-Level Registry**: Pinjected maintains a module-level registry of all injected components which requires them to be defined at module scope
4. **Predictable Dependencies**: All dependencies must be known at configuration time, not created dynamically during execution

## Examples

### ❌ Incorrect

```python
from pinjected import injected, instance

# Error: @injected inside regular function
def process_data(user_id: str):
    @injected  # PINJ027: Cannot define @injected inside function
    def fetch_user(database, /, uid: str):
        return database.get_user(uid)
    
    return fetch_user(user_id)

# Error: @instance inside class
class ServiceManager:
    @instance  # PINJ027: Cannot define @instance inside class
    def database(self, config, /):
        return DatabaseConnection(config)

# Error: @injected inside method
class DataProcessor:
    def setup(self):
        @injected  # PINJ027: Cannot define @injected inside method
        def logger(log_config, /):
            return create_logger(log_config)
        
        self.logger = logger()

# Error: Nested in conditional
def conditional_setup(debug_mode):
    if debug_mode:
        @injected  # PINJ027: Cannot define @injected inside if block
        def debug_logger(/, msg):
            print(f"DEBUG: {msg}")
        return debug_logger
```

### ✅ Correct

```python
from pinjected import injected, instance, design
from typing import Protocol

# All @injected and @instance definitions at module level
@injected
def fetch_user(database, /, uid: str):
    return database.get_user(uid)

@instance
def database_connection(config, /):
    """Instance defined at module level."""
    return DatabaseConnection(config)

@injected
def logger(log_config, /):
    return create_logger(log_config)

# Use regular functions for conditional logic
@injected
def debug_logger(/, msg):
    print(f"DEBUG: {msg}")

@injected
def prod_logger(/, msg):
    # Production logging logic
    pass

@injected
def get_logger(config, debug_logger, prod_logger, /):
    """Factory pattern for conditional dependencies."""
    return debug_logger if config.debug else prod_logger

# Classes can use injected dependencies
class ServiceManager:
    def __init__(self, database: DatabaseConnection):
        self.database = database

# Regular functions can be defined anywhere
def process_data(items):
    def helper(item):  # OK: Regular function without decorators
        return item * 2
    return [helper(item) for item in items]

# Configure dependencies
services = design(
    database=database_connection,
    logger=logger
)
```

## Key Principles

1. **Module-level only**: Both `@injected` and `@instance` decorators must be defined at module level, never inside functions or classes.

2. **Static dependency graph**: Dependencies are resolved at configuration time, not dynamically during execution.

3. **Use factory patterns**: For conditional dependencies, use factory functions that select between different implementations.

4. **Regular functions are unrestricted**: Only functions decorated with `@injected` or `@instance` have this restriction. Regular functions can be defined anywhere.

## How to Fix

1. **Move to module level**: Extract all `@injected` and `@instance` definitions to the module level
2. **Use dependency injection**: Instead of defining nested functions, inject them as dependencies
3. **Factory pattern**: For conditional dependencies, create a factory function that returns the appropriate implementation
4. **Regular helpers**: For simple helper functions that don't need dependency injection, use regular functions (without decorators)

## Configuration

This rule can be disabled in your `pyproject.toml`:

```toml
[tool.pinjected-linter]
disable = ["PINJ027"]
```

## Severity

**Error** - This violates pinjected's requirement that all dependency declarations must be at module level.

## See Also

- [PINJ028: No design() usage inside @injected functions](./pinj028_no_design_in_injected.md)
- [Pinjected Usage Guide - Building Dependency Graphs](https://github.com/pinjected/pinjected/blob/main/docs/how_to_use_pinjected.md)