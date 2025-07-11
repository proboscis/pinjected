# PINJ034: No Lambda or Non-Decorated Functions in design()

## Overview

This rule forbids assigning lambda functions or non-decorated functions (functions without `@injected` or `@instance`) to a design context. Only properly decorated functions should be used with design().

## Rationale

The design() context in pinjected is used to configure the dependency injection container. It expects functions that are part of the dependency graph - specifically those decorated with `@injected` or `@instance`. Using lambda functions or regular functions creates several problems:

1. **No Dependency Resolution**: Lambda and regular functions bypass pinjected's dependency injection mechanism
2. **Breaks Testability**: Can't override or mock these functions properly in tests
3. **Implicit Dependencies**: Lambda functions often capture variables from their enclosing scope, creating hidden dependencies
4. **Type Safety**: Pinjected can't properly type-check lambda functions
5. **Debugging**: Lambda functions are harder to debug and don't have meaningful names in error messages

## Examples

### ❌ Incorrect

```python
from pinjected import design, injected

# Error: Lambda function in design  
with design() as d:
    d['get_config'] = lambda: {'debug': True}  # PINJ034
    d['database'] = lambda: DatabaseConnection()  # PINJ034
    
# Error: Regular function without decorator
def create_logger():
    return Logger()

with design() as d:
    d['logger'] = create_logger  # PINJ034

# Or directly in design()
config = design(
    logger=create_logger  # PINJ034 - not decorated
)

# Error: Inline function definition
with design() as d:
    def get_user_service():  # Not decorated
        return UserService()
    d['user_service'] = get_user_service  # PINJ034

# Error: Lambda with dependencies
with design() as d:
    config = load_config()
    d['db'] = lambda: connect_db(config)  # PINJ034 - captures 'config'
```

### ✅ Correct

```python
from pinjected import design, injected, instance

# Correct: Use @injected for functions
@injected
def get_config():
    return {'debug': True}

@instance
def database_connection(config, /):
    return DatabaseConnection(config)

# Correct: Use @instance for factory functions
@instance
def logger():
    return Logger()

# Correct: Configure with decorated functions
service_design = design(
    config=get_config,
    database=database_connection,
    logger=logger
)

# Or using context manager
with design() as d:
    d['config'] = get_config
    d['database'] = database_connection  
    d['logger'] = logger
    
# Correct: Combine designs
base_design = design(
    config=get_config,
    database=database_connection
)

# Override with decorated functions  
@injected
def test_config():
    return {'debug': False}

test_design = base_design + design(
    config=test_config  # Overrides get_config
)
```

## Common Patterns to Refactor

### Pattern 1: Configuration Values
```python
# ❌ Wrong
with design() as d:
    d['api_key'] = lambda: 'secret-key'

# ✅ Correct
@instance
def api_key():
    return 'secret-key'

config = design(
    api_key=api_key
)

# Or using context manager
with design() as d:
    d['api_key'] = api_key
```

### Pattern 2: Factory Functions
```python
# ❌ Wrong
with design() as d:
    d['create_client'] = lambda config: Client(config['url'])

# ✅ Correct
@injected
def create_client(config, /):
    return Client(config['url'])

client_design = design(
    create_client=create_client
)
```

### Pattern 3: Conditional Dependencies
```python
# ❌ Wrong
with design() as d:
    if debug_mode:
        d['logger'] = lambda: DebugLogger()
    else:
        d['logger'] = lambda: ProductionLogger()

# ✅ Correct
@instance
def debug_logger():
    return DebugLogger()

@instance  
def production_logger():
    return ProductionLogger()

@injected
def logger(config, debug_logger, production_logger, /):
    return debug_logger if config['debug'] else production_logger

logging_design = design(
    logger=logger,
    debug_logger=debug_logger,
    production_logger=production_logger
)
```

## How to Fix

1. **Convert lambdas to @injected/@instance functions**: Extract lambda functions to module-level functions with appropriate decorators
2. **Add decorators to regular functions**: If using regular functions, add `@injected` or `@instance` decorators
3. **Use dependency injection**: Instead of capturing variables, inject them as dependencies
4. **Extract configuration**: Move configuration values to proper `@instance` functions

## Benefits of Following This Rule

1. **Testability**: Can easily override dependencies in tests
2. **Type Safety**: Proper type checking for all dependencies  
3. **Debugging**: Named functions with clear stack traces
4. **Maintainability**: Clear dependency graph visible at module level
5. **Consistency**: All dependencies follow the same pattern

## Configuration

This rule can be disabled in your `pyproject.toml`:

```toml
[tool.pinjected-linter]
disable = ["PINJ034"]
```

## Severity

**Error** - Using lambda or non-decorated functions in design() breaks pinjected's dependency injection pattern and should be avoided.

## See Also

- [PINJ001: Use @instance for class providers](./pinj001_prefer_instance_for_class_providers.md)
- [PINJ016: Always specify protocol parameter](./pinj016_always_specify_protocol.md) 
- [PINJ027: No nested @injected or @instance definitions](./pinj027_no_nested_injected.md)
- [Pinjected Documentation - design() API](https://pinjected.readthedocs.io/en/latest/api/design/)