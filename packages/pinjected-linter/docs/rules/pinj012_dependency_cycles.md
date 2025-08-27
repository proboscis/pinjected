# PINJ012: Dependency Cycles

## Overview

**Rule ID:** PINJ012  
**Category:** Dependency  
**Severity:** Error  
**Auto-fixable:** No

Circular dependencies between `@injected` functions will cause runtime errors in Pinjected. This rule detects dependency cycles at development time.

## Rationale

In Pinjected, `@injected` functions can declare other `@injected` functions as dependencies (before the `/` separator). When resolving these dependencies, Pinjected builds a dependency graph and attempts to resolve each dependency in order.

If there's a circular dependency chain (e.g., A → B → C → A), Pinjected will enter an infinite loop trying to resolve the dependencies, resulting in:

1. **Stack overflow errors** at runtime
2. **Difficult-to-debug issues** in production
3. **Unpredictable behavior** in the dependency injection system
4. **Poor code architecture** with tightly coupled components

This rule helps catch these issues during development, before they cause runtime failures.

## Rule Details

This rule analyzes all `@injected` functions in your codebase to:

1. Build a dependency graph from function signatures
2. Extract dependencies (parameters before the `/` separator)
3. Detect cycles using graph traversal algorithms
4. Report all circular dependency chains found

### Examples of Violations

❌ **Bad:** Simple circular dependency
```python
from pinjected import injected

@injected
def service_a(service_b, /):
    return f"A uses {service_b()}"

@injected
def service_b(service_a, /):  # Error: Creates cycle A → B → A
    return f"B uses {service_a()}"
```

❌ **Bad:** Complex circular dependency chain
```python
from pinjected import injected

@injected
def auth_service(user_service, /, request):
    user = user_service(request.user_id)
    return validate_auth(user)

@injected
def user_service(database_service, /, user_id):
    return database_service(f"SELECT * FROM users WHERE id={user_id}")

@injected
def database_service(logger_service, /, query):
    logger_service(f"Executing: {query}")
    return execute_query(query)

@injected
def logger_service(auth_service, /, message):  # Error: Creates cycle
    # auth_service → user_service → database_service → logger_service → auth_service
    if auth_service.is_admin():
        log_admin_action(message)
    return log(message)
```

❌ **Bad:** Self-referencing function
```python
from pinjected import injected

@injected
def recursive_service(recursive_service, /, data):  # Error: Self-reference
    if data:
        return recursive_service(data[1:])
    return []
```

✅ **Good:** Proper dependency hierarchy
```python
from pinjected import injected

# Good: Clear dependency hierarchy with no cycles
@injected
def api_handler(auth_service, user_service, /, request):
    if auth_service(request.token):
        return user_service(request.user_id)
    return {"error": "Unauthorized"}

@injected
def auth_service(token_validator, /, token):
    return token_validator(token)

@injected
def user_service(database, /, user_id):
    return database(f"SELECT * FROM users WHERE id={user_id}")

@injected
def token_validator(/, token):
    # No dependencies - leaf node
    return validate_jwt(token)

@injected
def database(logger, /, query):
    logger(f"Query: {query}")
    return execute_query(query)

@injected
def logger(/, message):
    # No dependencies - leaf node
    print(f"[LOG] {message}")
```

## Common Patterns and Best Practices

### 1. Design Clear Dependency Hierarchies

Structure your dependencies in layers:
```python
# Layer 1: Core utilities (no dependencies)
@injected
def logger(/, message): pass

@injected
def config(/, key): pass

# Layer 2: Services using core utilities
@injected
def database(logger, config, /, query): pass

# Layer 3: Business logic using services
@injected
def user_service(database, /, user_id): pass

# Layer 4: API/UI using business logic
@injected
def api_handler(user_service, auth_service, /, request): pass
```

### 2. Break Cycles with Interfaces

If you need bidirectional communication, use callbacks or events:
```python
# Instead of circular dependency, use callbacks
@injected
def notification_service(/, user_id, callback):
    # Send notification
    result = send_notification(user_id)
    if callback:
        callback(result)
    return result

@injected
def user_service(notification_service, /, user_id):
    def on_notification_sent(result):
        # Handle notification result
        update_user_notification_status(user_id, result)
    
    # Pass callback instead of creating circular dependency
    notification_service(user_id, on_notification_sent)
```

### 3. Use Shared Dependencies

Instead of services depending on each other, have them depend on shared lower-level services:
```python
# Bad: auth_service and user_service depend on each other
# Good: Both depend on a shared database service

@injected
def auth_service(database, /, token):
    # Use database directly
    return database("SELECT * FROM tokens WHERE token=?", token)

@injected
def user_service(database, /, user_id):
    # Use database directly
    return database("SELECT * FROM users WHERE id=?", user_id)
```

## Error Messages

The rule provides clear error messages showing the complete dependency cycle:

```
PINJ012: Circular dependency detected:
  service_a → service_b → service_c → service_a
```

For multiple cycles, each cycle is reported separately:
```
PINJ012: Multiple circular dependencies detected:
  Cycle 1: auth_service → user_service → auth_service
  Cycle 2: logger → monitor → logger
```

## Configuration

This rule has no configuration options. Circular dependencies are always an error.

## When to Refactor

If you encounter circular dependencies, consider these refactoring strategies:

1. **Extract shared functionality** to a lower-level service
2. **Use events or callbacks** for loose coupling
3. **Implement the Dependency Inversion Principle** with interfaces
4. **Split large services** into smaller, focused components
5. **Re-evaluate your architecture** if cycles are common

## Related Rules

- **PINJ008:** Injected dependency declaration (ensures dependencies are properly declared)
- **PINJ015:** Missing slash separator (ensures correct function signatures)

## See Also

- [Pinjected Documentation on Dependencies](https://pinjected.readthedocs.io/dependencies)
- [Dependency Injection Best Practices](https://pinjected.readthedocs.io/best-practices)
- [Circular Dependency Anti-pattern](https://en.wikipedia.org/wiki/Circular_dependency)

## Version History

- **1.0.0:** Initial implementation of circular dependency detection