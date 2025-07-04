# PINJ008: Injected Dependency Declaration

## Overview

**Rule ID:** PINJ008  
**Category:** Dependencies  
**Severity:** Error  
**Auto-fixable:** No

All dependency functions called within `@injected` functions must be declared as parameters before the `/` separator.

## Rationale

Pinjected requires explicit declaration of all dependencies used within an `@injected` function. This ensures:

1. **Explicit Dependencies:** All dependencies are visible in the function signature
2. **Dependency Resolution:** Pinjected knows what to inject
3. **Testability:** Easy to mock dependencies for testing
4. **No Hidden Dependencies:** Prevents implicit global dependencies
5. **Type Safety:** Enables proper type checking of dependencies

### Important: Understanding AST Building

When you call other `@injected` functions inside an `@injected` function, you're **building an AST (Abstract Syntax Tree)**, not executing functions directly. This is why:
- You must NOT use `await` when calling `@injected` functions inside other `@injected` functions
- The functions are not actually executed at definition time
- Pinjected builds a computation graph from these calls

## Rule Details

This rule ensures that any function called within an `@injected` function that could be a dependency is properly declared as a parameter before the `/` separator.

### Examples of Violations

❌ **Bad:** Using undeclared dependencies
```python
@injected
def process_user(logger, /, user_id: str):
    # Error: validate_user not declared
    if not validate_user(user_id):
        logger.error("Invalid user")
        return None
    
    # Error: fetch_user not declared
    user = fetch_user(user_id)
    
    # Error: transform_user not declared
    return transform_user(user)

@injected
async def a_sync_data(/, source: str, target: str):
    # Error: a_fetch_data not declared
    data = a_fetch_data(source)  # Note: No await - building AST
    
    # Error: a_save_data not declared
    a_save_data(target, data)  # Note: No await - building AST
```

✅ **Good:** All dependencies declared
```python
@injected
def process_user(
    logger,
    validate_user,  # Declared
    fetch_user,     # Declared
    transform_user, # Declared
    /,
    user_id: str
):
    if not validate_user(user_id):
        logger.error("Invalid user")
        return None
    
    user = fetch_user(user_id)
    return transform_user(user)

@injected
async def a_sync_data(
    a_fetch_data,  # Declared
    a_save_data,   # Declared
    /,
    source: str,
    target: str
):
    # Note: Do NOT use await when calling @injected functions
    # inside other @injected functions - you're building an AST
    data = a_fetch_data(source)
    a_save_data(target, data)
```

## Common Patterns and Best Practices

### 1. Declare all function dependencies
```python
# ❌ Bad - missing declarations
@injected
def create_order(logger, /, order_data: dict):
    # These should be declared
    if not validate_order(order_data):
        return None
    
    user = get_user(order_data["user_id"])
    inventory = check_inventory(order_data["items"])
    
    order = Order(user, inventory)
    save_order(order)
    
    send_confirmation_email(user.email, order)
    return order

# ✅ Good - all declared
@injected
def create_order(
    logger,
    validate_order,
    get_user,
    check_inventory,
    save_order,
    send_confirmation_email,
    /,
    order_data: dict
):
    if not validate_order(order_data):
        return None
    
    user = get_user(order_data["user_id"])
    inventory = check_inventory(order_data["items"])
    
    order = Order(user, inventory)
    save_order(order)
    
    send_confirmation_email(user.email, order)
    return order
```

### 2. Group related dependencies
```python
# ✅ Good - organized declarations
@injected
def process_payment(
    # Logging
    logger,
    metrics,
    
    # Validation
    validate_payment,
    validate_customer,
    
    # External services
    payment_gateway,
    fraud_detector,
    
    # Data access
    save_transaction,
    update_balance,
    /,
    payment_data: dict
):
    # Implementation using all declared dependencies
    pass
```

### 3. Handle async dependencies
```python
# ✅ Good - async dependencies with a_ prefix
@injected
async def a_process_batch(
    logger,
    a_fetch_items,      # Async dependency
    validate_item,      # Sync dependency
    a_transform_item,   # Async dependency
    a_save_results,     # Async dependency
    /,
    batch_id: str
):
    # IMPORTANT: No await when calling @injected functions!
    # You're building an AST, not executing
    items = a_fetch_items(batch_id)
    
    # Note: This is a simplified example - in reality,
    # the AST building would handle the iteration
    results = []
    for item in items:
        if validate_item(item):
            transformed = a_transform_item(item)
            results.append(transformed)
    
    a_save_results(batch_id, results)
    logger.info(f"Processed batch {batch_id}")
```

### 4. Don't declare non-dependency functions
```python
# ✅ Good - only actual dependencies declared
@injected
def calculate_price(
    tax_calculator,  # Dependency
    discount_service,  # Dependency
    /,
    base_price: float,
    quantity: int
):
    # These are not dependencies, just helper functions
    def apply_bulk_discount(price, qty):
        if qty > 10:
            return price * 0.9
        return price
    
    # Standard library functions don't need declaration
    subtotal = round(base_price * quantity, 2)
    
    # Only injected dependencies are called
    tax = tax_calculator.calculate(subtotal)
    discount = discount_service.get_discount(quantity)
    
    return subtotal + tax - discount
```

## What Counts as a Dependency?

Dependencies that must be declared:
- Functions decorated with `@injected`
- Functions decorated with `@instance`
- Any function that could be provided through dependency injection

Not dependencies (don't declare):
- Standard library functions (`len()`, `print()`, `round()`)
- Built-in functions
- Lambda functions defined inline
- Class methods called on objects
- Functions imported from external libraries

## Configuration

This rule has no configuration options.

## When to Disable

You might want to disable this rule if:
- Working with legacy code during migration
- Using a different dependency injection pattern

To disable for a specific function:
```python
# noqa: PINJ008
@injected
def legacy_function(logger, /):
    # Legacy code with implicit dependencies
    result = some_global_function()
    return result
```

To disable in configuration:
```toml
[tool.pinjected-linter]
disable = ["PINJ008"]
```

## Related Rules

- **PINJ015:** Missing slash separator (ensures proper parameter separation)
- **PINJ011:** IProxy annotations (proper typing of dependencies)

## See Also

- [Pinjected @injected documentation](https://pinjected.readthedocs.io/injected)
- [Dependency Injection Best Practices](https://www.martinfowler.com/articles/injection.html)

## Version History

- **1.0.0:** Initial implementation