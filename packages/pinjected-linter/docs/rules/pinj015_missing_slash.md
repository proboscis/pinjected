# PINJ015: Missing Slash in @injected Functions

## Overview

**Rule ID:** PINJ015  
**Category:** Syntax  
**Severity:** Warning  
**Auto-fixable:** No

`@injected` functions typically use the `/` separator to distinguish dependencies from runtime arguments. Without `/`, ALL arguments are treated as runtime arguments, which may be intentional in some cases.

## Rationale

The `/` separator is CRITICAL in Pinjected because it defines the boundary between:

1. **Dependencies (before `/`):** Arguments that are injected by Pinjected
2. **Runtime Arguments (after `/`):** Arguments that must be provided when calling

**Without `/`, Pinjected treats ALL arguments as runtime arguments**, meaning:
- No dependency injection occurs
- All arguments must be provided at call time
- The function behaves like a regular Python function
- The `@injected` decorator is still building a dependency graph node, but with no dependencies

While this is sometimes intentional (e.g., for pure transformation functions), it's often a mistake.

## Rule Details

This rule warns when `@injected` functions have arguments but no `/` separator, unless explicitly marked as intentional with `pinjected: no dependencies`.

### Examples of Violations

❌ **Bad:** Missing slash - NO injection happens!
```python
@injected
def process_order(database, logger, order_id: str):
    # ERROR: Without '/', ALL args are runtime args
    # This means database and logger are NOT injected
    # You must call it like: process_order(db_instance, logger_instance, "123")
    logger.info(f"Processing order {order_id}")
    return database.get_order(order_id)

@injected
async def a_fetch_user(cache, database, user_id: str):
    # ERROR: No dependencies will be injected!
    # Must provide cache and database when calling
    cached = await cache.get(user_id)
    if not cached:
        cached = await database.get_user(user_id)
    return cached
```

✅ **Good:** Proper slash usage
```python
@injected
def process_order(database, logger, /, order_id: str):
    # CORRECT: database and logger are injected
    # Only order_id needs to be provided when calling
    logger.info(f"Processing order {order_id}")
    return database.get_order(order_id)

@injected
async def a_fetch_user(cache, database, /, user_id: str):
    # CORRECT: cache and database are injected
    # Only user_id is a runtime argument
    cached = await cache.get(user_id)
    if not cached:
        cached = await database.get_user(user_id)
    return cached

@injected
def get_config(config_service, /):
    # CORRECT: All dependencies, no runtime args
    return config_service.get_all()

@injected
def transform_data(data: dict) -> dict:
    """Transform data without any dependencies.
    
    pinjected: no dependencies
    """
    # CORRECT: Explicitly marked as having no dependencies
    return {k: v.upper() for k, v in data.items()}
```

## Common Mistakes and Their Consequences

### 1. Forgetting the slash completely
```python
# ❌ WRONG - No injection happens!
@injected
def create_user(validator, database, user_data: dict):
    # validator and database are NOT injected
    # Must call like: create_user(validator_obj, db_obj, {...})
    if validator.validate(user_data):
        return database.create_user(user_data)

# ✅ CORRECT - Dependencies are injected
@injected
def create_user(validator, database, /, user_data: dict):
    # validator and database ARE injected
    # Call like: create_user({"name": "John"})
    if validator.validate(user_data):
        return database.create_user(user_data)
```

### 2. Slash in wrong position
```python
# ❌ WRONG - user_service becomes runtime arg
@injected
def update_profile(user_id: str, /, user_service, data: dict):
    # user_service is AFTER slash, so it's NOT injected
    return user_service.update(user_id, data)

# ✅ CORRECT - user_service is injected
@injected
def update_profile(user_service, /, user_id: str, data: dict):
    # user_service is BEFORE slash, so it IS injected
    return user_service.update(user_id, data)
```

### 3. All dependencies, no runtime args
```python
# ❌ WRONG - No slash means logger is NOT injected
@injected
def startup_tasks(logger, config_loader, task_runner):
    # ALL three must be provided when calling!
    logger.info("Starting tasks...")
    config = config_loader.load()
    task_runner.run(config)

# ✅ CORRECT - All are dependencies
@injected
def startup_tasks(logger, config_loader, task_runner, /):
    # All three are injected, no args needed when calling
    logger.info("Starting tasks...")
    config = config_loader.load()
    task_runner.run(config)
```

## Understanding the Impact

### Without slash - Manual injection required:
```python
@injected
def process_payment(payment_gateway, logger, amount, customer_id):
    # NO SLASH = NO INJECTION
    # Must manually provide ALL arguments:
    
# Usage without slash (wrong):
gateway = PaymentGateway()
logger = Logger()
process_payment(gateway, logger, 100.00, "cust123")  # Manual!

### With slash - Automatic injection:
```python
@injected
def process_payment(payment_gateway, logger, /, amount, customer_id):
    # WITH SLASH = AUTOMATIC INJECTION
    
# Usage with slash (correct):
process_payment(100.00, "cust123")  # Dependencies injected!
```

## Intentional No-Dependencies Pattern

Sometimes you genuinely want an `@injected` function with no dependencies (all runtime arguments). This is valid for:
- Pure transformation functions
- Validation functions
- Utility functions that need to be part of the dependency graph

To indicate this is intentional, add `pinjected: no dependencies` to the docstring:

```python
@injected
def validate_email(email: str) -> bool:
    """Validate email format.
    
    pinjected: no dependencies
    """
    return "@" in email and "." in email

@injected
def normalize_user_data(data: dict) -> dict:
    """Normalize user data for consistency.
    
    This is a pure function with no dependencies.
    pinjected: no dependencies
    """
    return {
        "name": data.get("name", "").strip().title(),
        "email": data.get("email", "").lower()
    }
```

## Migration Guide

When fixing missing slash warnings:

1. **First, determine if no dependencies is intentional:**
   - If yes: Add `pinjected: no dependencies` to the docstring
   - If no: Add the `/` separator appropriately

2. **Identify intended dependencies vs runtime args:**
   ```python
   # Before (broken):
   @injected
   def handle_request(auth_service, router, request_data):
       pass
   
   # Ask: What should be injected vs provided at runtime?
   # - auth_service: dependency (inject)
   # - router: dependency (inject)  
   # - request_data: runtime data (provide when calling)
   
   # After (fixed):
   @injected
   def handle_request(auth_service, router, /, request_data):
       pass
   ```

2. **Common dependency patterns:**
   - Services, clients, repositories → Before `/`
   - Data, IDs, parameters → After `/`
   - Loggers, validators, processors → Before `/`
   - User input, requests, events → After `/`

3. **All dependencies, no runtime args:**
   ```python
   # Before:
   @injected
   def initialize_system(logger, database, cache, metrics):
       pass
   
   # After (slash at end):
   @injected  
   def initialize_system(logger, database, cache, metrics, /):
       pass
   ```

## Configuration

This rule has no configuration options.

## When to Disable

This rule should rarely be disabled. Instead:
- If no dependencies is intentional: Add `pinjected: no dependencies` to the docstring
- If dependencies are needed: Add the `/` separator

The only valid reasons to disable might be:
- During initial migration when learning Pinjected
- Legacy code that will be refactored soon

To disable for a specific function:
```python
# noqa: PINJ015
@injected
def legacy_function(service, data):  # Will fix urgently!
    pass
```

To disable in configuration:
```toml
[tool.pinjected-linter]
disable = ["PINJ015"]
```

## Related Rules

- **PINJ009:** No direct calls to @injected functions
- **PINJ011:** IProxy annotations (for dependency types)
- **PINJ017:** Missing type annotations for dependencies

## See Also

- [Python PEP 570 - Positional-Only Parameters](https://www.python.org/dev/peps/pep-0570/)
- [Pinjected @injected documentation](https://pinjected.readthedocs.io/injected)
- [Dependency Injection Patterns](https://pinjected.readthedocs.io/patterns)

## Version History

- **1.1.0:** Changed from Error to Warning, added `pinjected: no dependencies` marker support
- **1.0.0:** Initial implementation