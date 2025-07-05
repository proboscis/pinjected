# PINJ007: Slash Separator Position

## Overview

**Rule ID:** PINJ007  
**Category:** Injection  
**Severity:** Error  
**Auto-fixable:** No

The `/` separator must correctly separate injected dependencies (left) from runtime arguments (right).

## Rationale

The slash separator (`/`) in `@injected` functions is a critical syntactic element that clearly delineates:
- **Left side:** Parameters that are dependency-injected by Pinjected
- **Right side:** Parameters that must be provided at runtime when calling the function

Incorrect placement of the slash separator will cause runtime errors because:
1. Dependencies placed after `/` won't be injected
2. The function will expect these as runtime arguments
3. Calls will fail with missing argument errors

## Rule Details

This rule verifies that all dependency parameters appear before the `/` separator in `@injected` functions. It uses various heuristics to identify likely dependencies:

1. Known dependency names from `@instance` and `@injected` functions in the codebase
2. Common dependency naming patterns (logger, db, cache, service, etc.)
3. Parameters with dependency-like suffixes (_service, _client, _manager, etc.)
4. Parameters used as method calls in the function body
5. Async dependency patterns (a_ prefix)

### Examples of Violations

❌ **Bad:** Dependencies after the slash
```python
@injected
def process(dep1, /, dep2, arg):  # ❌ dep2 on wrong side
    return dep1.process(dep2, arg)

@injected
def handle(/, logger, data):  # ❌ logger should be on left
    logger.info(f"Processing {data}")

@injected
def compute(calc, /, transformer, value):  # ❌ transformer on wrong side
    return calc.compute(transformer.transform(value))

@injected
def mixed(db, /, cache, user_id):  # ❌ cache is a dependency
    cached = cache.get(user_id)  # This would fail at runtime!
    return cached or db.fetch(user_id)

@injected
async def a_process(/, a_fetch_data, id):  # ❌ async dependency on wrong side
    data = a_fetch_data(id)
    return data.process()
```

✅ **Good:** Correct slash placement
```python
@injected
def process(dep1, dep2, /, arg):  # ✅ Dependencies on left
    return dep1.process(dep2, arg)

@injected
def handle(logger, /, data):  # ✅ Logger on left
    logger.info(f"Processing {data}")

@injected
def compute(calc, transformer, /, value):  # ✅ Dependencies on left
    return calc.compute(transformer.transform(value))

@injected
def mixed(db, cache, /, user_id):  # ✅ All dependencies on left
    cached = cache.get(user_id)
    return cached or db.fetch(user_id)

@injected
def no_deps(/, arg1, arg2):  # ✅ No dependencies is valid
    return arg1 + arg2

@injected
async def a_process(a_fetch_data, /, id):  # ✅ Async dependency on left
    data = a_fetch_data(id)
    return data.process()
```

## Common Patterns and Best Practices

### 1. Service dependencies
```python
# ❌ Bad - services are dependencies
@injected
def create_order(/, order_service, payment_service, order_data):
    # This will fail - services won't be injected
    payment = payment_service.process(order_data.amount)
    return order_service.create(order_data, payment)

# ✅ Good - services before slash
@injected
def create_order(order_service, payment_service, /, order_data):
    payment = payment_service.process(order_data.amount)
    return order_service.create(order_data, payment)
```

### 2. Logger placement
```python
# ❌ Bad - logger is always a dependency
@injected
def process_request(validator, /, logger, request):
    logger.info(f"Processing request {request.id}")
    return validator.validate(request)

# ✅ Good - logger before slash
@injected
def process_request(validator, logger, /, request):
    logger.info(f"Processing request {request.id}")
    return validator.validate(request)
```

### 3. Configuration and context
```python
# ❌ Bad - config/context are dependencies
@injected
def initialize_system(/, config, context, options):
    return System(
        config.get_database_url(),
        context.get_user(),
        options
    )

# ✅ Good - dependencies before slash
@injected
def initialize_system(config, context, /, options):
    return System(
        config.get_database_url(),
        context.get_user(),
        options
    )
```

## Dependency Detection Heuristics

The rule uses several methods to identify dependencies:

### 1. Known dependencies
```python
# If you have these in your codebase:
@instance
def database():
    return Database()

@injected
def user_service(database, /):
    return UserService(database)

# Then 'database' and 'user_service' are recognized as dependencies
@injected
def get_user(/, database, user_id):  # ❌ 'database' detected as dependency
    return database.get_user(user_id)
```

### 2. Common patterns
```python
# These are recognized as likely dependencies:
- logger, db, database, cache, redis
- api, client, service, repository, repo
- manager, handler, processor, transformer
- validator, serializer, parser, formatter
- auth, authenticator, session, store
- queue, broker, publisher, factory
- config, settings, context, engine
```

### 3. Suffix patterns
```python
# Parameters ending with these suffixes are likely dependencies:
@injected
def process(/, user_service, payment_client, data):  # ❌ Both detected
    # _service and _client suffixes indicate dependencies
    pass
```

### 4. Usage patterns
```python
@injected
def handle(/, processor, data):  # ❌ Detected by usage
    # 'processor' is used as an object with methods
    result = processor.process(data)
    processor.log_result(result)
    return result
```

## When This Rule Doesn't Apply

This rule only checks `@injected` functions. It doesn't apply to:
- Regular functions without decorators
- `@instance` decorated functions
- Functions without a `/` separator (handled by PINJ015)

## Configuration

This rule has no configuration options.

## When to Disable

You should rarely disable this rule as incorrect slash placement will cause runtime errors. Only disable when:
- You're using a custom injection system with different conventions
- During migration when gradually fixing legacy code

To disable for a specific function:
```python
# noqa: PINJ007
@injected
def legacy_function(arg1, /, dependency, arg2):
    # Will be fixed in next refactor
    pass
```

To disable in configuration:
```toml
[tool.pinjected-linter]
disable = ["PINJ007"]
```

## Related Rules

- **PINJ008:** Injected dependency declaration
- **PINJ015:** Missing slash in @injected functions

## See Also

- [Pinjected Documentation - @injected decorator](https://pinjected.readthedocs.io/injected)
- [PEP 570 - Positional-Only Parameters](https://www.python.org/dev/peps/pep-0570/)

## Version History

- **1.0.0:** Initial implementation matching Linear issue ARC-290