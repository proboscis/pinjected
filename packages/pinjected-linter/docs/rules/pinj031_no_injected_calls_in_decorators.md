# PINJ031: No Calls to injected() Inside @instance/@injected Functions

## Overview

Inside `@instance` and `@injected` functions, you're building a dependency graph, not executing code. Calling `injected()` inside these functions indicates a fundamental misunderstanding of how pinjected works.

This rule detects and prevents calls to the `injected()` function within functions decorated with `@instance` or `@injected`.

## Rationale

The `@instance` and `@injected` decorators are part of Pinjected's dependency injection system:

1. **@instance** - Defines singleton instances in the dependency graph
2. **@injected** - Defines factory functions in the dependency graph
3. **injected()** - A function used to request dependencies from the dependency injection container

Key principle: **Don't call injected() inside dependency graph definitions**. The `injected()` function is meant to be used at the application's entry points or in regular (non-decorated) functions, not within the dependency graph itself.

## Examples

### ❌ Incorrect

```python
from pinjected import instance, injected

@instance
def my_service():
    # ERROR: Calling injected() inside @instance
    dep = injected(SomeDependency)
    return ServiceImpl(dep)

@injected
def process_data(logger, /, data):
    # ERROR: Calling injected() inside @injected
    processor = injected(DataProcessor)
    return processor.process(data)

@instance
def complex_service():
    # ERROR: Multiple injected() calls in various forms
    deps = [injected(Dep1), injected(Dep2)]
    config = {'handler': injected(Handler)}
    return Service(deps, config)
```

### ✅ Correct

```python
from pinjected import instance, injected

@instance
def my_service(some_dependency: SomeDependency):
    # CORRECT: Dependencies declared as parameters
    return ServiceImpl(some_dependency)

@injected
def process_data(logger: Logger, processor: DataProcessor, /, data):
    # CORRECT: Dependencies declared before the slash
    return processor.process(data)

# Using injected() in regular functions is OK
def main():
    # OK: injected() used in non-decorated function
    service = injected(MyService)
    service.run()
```

## Common Mistakes

### Mistake 1: Trying to dynamically inject dependencies

```python
# Wrong
@instance
def dynamic_service():
    if condition:
        dep = injected(ProdDependency)  # ERROR
    else:
        dep = injected(DevDependency)   # ERROR
    return Service(dep)

# Correct - Use separate instances
@instance
def prod_service(dep: ProdDependency):
    return Service(dep)

@instance
def dev_service(dep: DevDependency):
    return Service(dep)
```

### Mistake 2: Nested injected() calls

```python
# Wrong
@instance
def nested_service():
    # ERROR: injected() in complex expressions
    service = create_service(
        injected(Config),
        injected(Logger)
    )
    return service

# Correct
@instance
def nested_service(config: Config, logger: Logger):
    return create_service(config, logger)
```

### Mistake 3: Using injected() in class methods

```python
# Wrong
class ServiceFactory:
    @instance
    def create_service(self):
        # ERROR: injected() in @instance method
        dep = injected(Dependency)
        return Service(dep)

# Correct
class ServiceFactory:
    @instance
    def create_service(self, dependency: Dependency):
        return Service(dependency)
```

## Understanding the Error

When you see this error, it means you're trying to use runtime dependency injection inside a dependency graph definition. Remember:

1. **@instance/@injected functions define the graph** - They describe how to build components
2. **Dependencies are parameters** - All dependencies should be function parameters
3. **injected() is for runtime** - Use it only outside the dependency graph

## Migration Guide

If you're migrating from a different dependency injection pattern:

```python
# Old pattern (wrong for pinjected)
@instance
def service():
    db = injected(Database)
    cache = injected(Cache)
    return Service(db, cache)

# New pattern (correct)
@instance
def service(database: Database, cache: Cache):
    return Service(database, cache)
```

## Suppressing with noqa

This error should rarely be suppressed, but if necessary during migration:

```python
@instance
def legacy_service():
    # Legacy code being migrated
    dep = injected(Dependency)  # noqa: PINJ031 - Migration in progress
    return Service(dep)
```

**Important**: Always provide a reason when using `noqa` to suppress this error.

## Configuration

This rule cannot be disabled as it catches a fundamental misuse of pinjected.

## Severity

**Error** - This is always an error because it represents a fundamental misunderstanding of how dependency injection works in Pinjected.

## See Also

- [Pinjected Documentation](https://github.com/pinjected/pinjected)
- PINJ009: No direct calls to @injected functions
- PINJ032: @injected/@instance functions should not have IProxy return type