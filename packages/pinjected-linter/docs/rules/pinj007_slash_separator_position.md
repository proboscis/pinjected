# PINJ007: Slash Separator Position

## Overview

**Rule ID:** PINJ007  
**Category:** Injection  
**Severity:** Error  
**Auto-fixable:** No

**Note:** This rule is currently disabled as it cannot reliably determine developer intent.

## Rationale

The slash separator (`/`) in `@injected` functions is a critical syntactic element that clearly delineates:
- **Left side:** Parameters that are dependency-injected by Pinjected
- **Right side:** Parameters that must be provided at runtime when calling the function

While incorrect placement of the slash separator will cause runtime errors, this rule has been disabled because:
1. **Intent is unknowable:** A parameter named "logger" after `/` might be intentional, not a mistake
2. **False positives:** Heuristics can incorrectly flag legitimate runtime parameters
3. **Developer autonomy:** Developers should decide their parameter placement

## Current Status

This rule is effectively disabled. It will not produce any violations. The check for missing slash separators is handled by PINJ015.

## Historical Context

Previously, this rule attempted to detect potentially misplaced parameters using heuristics. Here are examples of what it would have flagged:

### What Would Have Been Flagged (No Longer Active)
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

## Why These Patterns Are No Longer Flagged

The rule previously used heuristics to detect potentially misplaced dependencies based on:
- Known dependency names
- Common patterns (logger, db, service, etc.)
- Suffix patterns (_service, _client, etc.)
- Usage patterns in the function body

However, these heuristics were disabled because:
1. **False positives:** A parameter named "logger" might legitimately be a runtime argument
2. **Developer intent:** Only the developer knows whether parameter placement is intentional
3. **Flexibility:** Some patterns might have valid use cases as runtime parameters

## When This Rule Applies

Since this rule is disabled, it effectively doesn't apply to any code. The rule exists for backward compatibility but will not produce violations.

## Configuration

This rule has no configuration options.

## Disabling This Rule

Since the rule is already effectively disabled, there's no need to explicitly disable it. However, if you want to ensure it's excluded:

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
- **1.1.0:** Rule disabled - heuristics cannot reliably determine developer intent