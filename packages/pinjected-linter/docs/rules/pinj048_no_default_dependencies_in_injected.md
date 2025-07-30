# PINJ048: No Default Values for Dependencies in @injected Functions

## Overview

**Rule ID:** PINJ048  
**Category:** Design  
**Severity:** Error  
**Auto-fixable:** No

Dependencies in `@injected` functions (parameters before the `/` separator) should not have default values. Configuration should be provided through the `design()` function instead.

## Rationale

Default values for dependencies in `@injected` functions are misleading and should be avoided:

1. **No Effect:** Default values in the dependency part (before `/`) are completely ignored by pinjected - they have no runtime effect
2. **Misleading Code:** Developers might think dependencies are optional when they're actually always injected
3. **False Expectations:** Code readers may assume the function can work without certain dependencies when it cannot
4. **Maintenance Confusion:** Future maintainers might waste time trying to understand why defaults aren't working
5. **Design Clarity:** Dependencies should clearly indicate they are always required and injected

**Important:** Default values DO work for runtime arguments (after `/`), but are silently ignored for dependencies.

## Rule Details

This rule flags any `@injected` function where dependency parameters (those before the `/` separator) have default values.

### Examples of Violations

❌ **Bad:** Dependencies with default values (which are ignored!)
```python
@injected
def process_order(logger=None, database=None, /, order_id: str):
    # ERROR: The =None defaults are IGNORED by pinjected
    # logger and database will ALWAYS be injected, never None
    # The if checks below will never be False!
    if logger:  # This check is meaningless
        logger.info(f"Processing order {order_id}")
    return database.get_order(order_id) if database else None

@injected
def fetch_user(cache=None, database=None, /, user_id: str):
    # ERROR: Defaults suggest these are optional, but they're NOT
    # cache and database will always be injected
    if cache:  # Always True - misleading!
        cached = cache.get(user_id)
        if cached:
            return cached
    return database.get_user(user_id) if database else None

@injected
def send_notification(email_service=EmailService(), /, message: str):
    # ERROR: The default EmailService() is NEVER used
    # email_service will always be injected from design
    email_service.send(message)

@injected
def analyze_data(processor=None, validator=None, config=None, /, data: dict):
    # ERROR: All these =None are ignored, dependencies always injected
    # The defensive checks below create false sense of optionality
    if validator and not validator.validate(data):
        return None
    return processor.process(data) if processor else data
```

✅ **Good:** Dependencies without defaults
```python
@injected
def process_order(logger, database, /, order_id: str):
    # CORRECT: All dependencies are required
    logger.info(f"Processing order {order_id}")
    return database.get_order(order_id)

@injected
def fetch_user(cache, database, /, user_id: str):
    # CORRECT: Both dependencies will be injected
    cached = cache.get(user_id)
    if cached:
        return cached
    return database.get_user(user_id)

@injected
def send_notification(email_service, /, message: str):
    # CORRECT: Service will be injected
    email_service.send(message)

@injected
def analyze_data(processor, validator, config, /, data: dict):
    # CORRECT: All dependencies required
    if not validator.validate(data):
        raise ValueError("Invalid data")
    return processor.process(data)
```

## Common Patterns and Solutions

### 1. Optional Dependencies

❌ **Bad:** Using defaults for optional dependencies
```python
@injected
def process_request(auth_service=None, logger=None, /, request):
    if auth_service and not auth_service.is_authorized(request):
        return {"error": "Unauthorized"}
    if logger:
        logger.info("Processing request")
    return {"status": "ok"}
```

✅ **Good:** Handle optionality in design
```python
# Option 1: Make dependencies required
@injected
def process_request(auth_service, logger, /, request):
    if not auth_service.is_authorized(request):
        return {"error": "Unauthorized"}
    logger.info("Processing request")
    return {"status": "ok"}

# Option 2: Create a null object pattern
class NullLogger:
    def info(self, msg): pass
    def error(self, msg): pass

@injected
def process_request(auth_service, logger, /, request):
    # logger might be NullLogger from design
    if not auth_service.is_authorized(request):
        return {"error": "Unauthorized"}
    logger.info("Processing request")
    return {"status": "ok"}

# Configure in design
design(logger=NullLogger())
```

### 2. Configuration Values

❌ **Bad:** Default configuration in function signature
```python
@injected
def create_connection(host="localhost", port=5432, /, database_name: str):
    return Connection(host, port, database_name)
```

✅ **Good:** Configuration through design
```python
@injected
def create_connection(host, port, /, database_name: str):
    return Connection(host, port, database_name)

# Configure in design
base_design = design(
    host="localhost",
    port=5432
)
```

### 3. Feature Flags

❌ **Bad:** Default feature flags
```python
@injected
def process_payment(payment_gateway, feature_flags=None, /, amount: float):
    if feature_flags and feature_flags.get("new_payment_flow"):
        return payment_gateway.process_v2(amount)
    return payment_gateway.process_v1(amount)
```

✅ **Good:** Explicit feature flag injection
```python
@injected
def process_payment(payment_gateway, feature_flags, /, amount: float):
    if feature_flags.get("new_payment_flow"):
        return payment_gateway.process_v2(amount)
    return payment_gateway.process_v1(amount)

# Configure in design
design(feature_flags={"new_payment_flow": True})
```

### 4. Runtime Arguments After Slash

Remember that default values ARE allowed for runtime arguments (after `/`):

```python
@injected
def search_products(database, logger, /, query: str, limit: int = 10):
    # CORRECT: 'limit' is a runtime argument with default
    logger.info(f"Searching for: {query}")
    return database.search(query, limit=limit)
```

## Migration Guide

When fixing violations of this rule:

1. **Remove default values from dependencies:**
   ```python
   # Before:
   @injected
   def service(logger=None, config=None, /, data):
       pass
   
   # After:
   @injected
   def service(logger, config, /, data):
       pass
   ```
   
   **Note:** This change is purely cosmetic - it doesn't change runtime behavior since defaults were already ignored. However, it makes the code clearer and prevents confusion.

2. **Handle optional dependencies in design:**
   ```python
   # Create appropriate null objects or use design variants
   prod_design = design(
       logger=Logger(),
       config=Config()
   )
   
   test_design = design(
       logger=NullLogger(),
       config=TestConfig()
   )
   ```

3. **For truly optional features, use explicit patterns:**
   ```python
   # Instead of optional dependency
   @injected
   def handler(metrics, /, request):
       # metrics might be MetricsCollector or NullMetrics
       metrics.record("request_received")
       return process(request)
   ```

## Configuration

This rule has no configuration options.

## When to Disable

This rule should rarely be disabled. If you need optional dependencies:

1. Use the Null Object pattern
2. Create different designs for different scenarios
3. Use `design().provide()` to conditionally provide dependencies

Only disable if:
- Migrating legacy code that extensively uses this pattern
- Working with third-party decorators that require defaults

To disable for a specific function:
```python
# noqa: PINJ048
@injected
def legacy_handler(old_service=None, /, data):  # Will refactor
    pass
```

To disable in configuration:
```toml
[tool.pinjected-linter]
disable = ["PINJ048"]
```

## Related Rules

- **PINJ002:** Instance function default arguments (similar rule for @instance)
- **PINJ015:** Missing slash in @injected functions
- **PINJ017:** Missing dependency type annotations
- **PINJ045:** No mode parameters (prevents runtime behavior switching)

## See Also

- [Pinjected @injected documentation](https://pinjected.readthedocs.io/injected)
- [Pinjected design() function documentation](https://pinjected.readthedocs.io/design)
- [Dependency Injection Best Practices](https://pinjected.readthedocs.io/best-practices)

## Version History

- **1.0.0:** Initial implementation