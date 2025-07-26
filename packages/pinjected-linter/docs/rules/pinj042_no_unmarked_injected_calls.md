# PINJ042: No Unmarked Calls to @injected Functions

## Overview

This rule forbids calling `@injected` functions from non-`@injected` contexts without explicitly marking the call as intentional. `@injected` functions are designed to be used through the dependency injection system, and direct calls bypass the entire DI framework.

This rule complements PINJ009:
- **PINJ009**: Handles calls *within* `@injected` functions (must declare as dependency)
- **PINJ042**: Handles calls *outside* `@injected` functions (must mark as intentional)

## Rationale

**Critical Understanding**: When you call an `@injected` function directly, it returns an `IProxy` object, NOT the actual function! This is why direct calls are forbidden.

### What Actually Happens

```python
@injected
def service(db, logger, /, data):
    return db.query(data)

# ❌ WRONG: This returns IProxy, not a result!
result = service("SELECT * FROM users")  # result is IProxy[...], not query results!
```

### Why This Is a Problem

1. **Returns IProxy, Not Function**: Direct calls to `@injected` functions return `IProxy` objects that need resolution
2. **Unresolved Dependencies**: The function's dependencies (db, logger) are not injected
3. **No Runtime Execution**: The IProxy is just a placeholder - it doesn't execute your code
4. **Type Confusion**: You expect the function's return value but get an IProxy wrapper
5. **Runtime Errors**: Attempting to use the IProxy as if it were the actual result will fail

### The Correct Mental Model

- `@injected` functions are **dependency declarations**, not executable functions
- They must be **resolved** through the DI system before they can be called
- Only **resolved functions** can accept runtime arguments and return actual values

## Examples

### ❌ Incorrect

```python
from pinjected import injected

@injected
def email_service(smtp_client, logger, /, recipient: str, message: str):
    logger.info(f"Sending email to {recipient}")
    return smtp_client.send(recipient, message)

# Regular function calling @injected without marking
def send_notification(user_email: str):
    # ERROR: Direct call to @injected function without marking
    email_service(user_email, "Welcome!")  
    
class NotificationHandler:
    def notify(self, email: str):
        # ERROR: Direct call from method
        result = email_service(email, "Alert!")
        return result

# Lambda calling @injected
process_emails = lambda emails: [
    email_service(e, "Bulk message")  # ERROR: Unmarked call
    for e in emails
]

# Nested function
def create_emailer():
    def send(addr):
        # ERROR: Unmarked call in nested function
        return email_service(addr, "Hello")
    return send
```

### ✅ Correct - Option 1: Mark as Intentional

```python
from pinjected import injected

@injected
def email_service(smtp_client, logger, /, recipient: str, message: str):
    logger.info(f"Sending email to {recipient}")
    return smtp_client.send(recipient, message)

# Mark with explicit comment
def send_notification(user_email: str):
    # CORRECT: Explicitly marked as intentional
    email_service(user_email, "Welcome!")  # pinjected: explicit-call
    
class NotificationHandler:
    def notify(self, email: str):
        # CORRECT: Using noqa to suppress
        result = email_service(email, "Alert!")  # noqa: PINJ042
        return result

# For testing or special cases
def test_email_service():
    # CORRECT: Marked for testing purposes
    result = email_service("test@example.com", "Test")  # pinjected: explicit-call
    assert result.success
```

### ✅ Correct - Option 2: Use Dependency Injection

```python
from pinjected import injected, instance

@injected
def email_service(smtp_client, logger, /, recipient: str, message: str):
    logger.info(f"Sending email to {recipient}")
    return smtp_client.send(recipient, message)

# Convert to @injected function
@injected
def send_notification(email_service, /, user_email: str):
    # CORRECT: email_service is now a dependency
    email_service(user_email, "Welcome!")

# Or use @instance for entry points
@instance
def notification_handler(email_service):
    class Handler:
        def notify(self, email: str):
            # CORRECT: Using injected email_service
            return email_service(email, "Alert!")
    return Handler()
```

### ✅ Correct - Option 3: Run Through DI System

```python
from pinjected import injected, Design
import asyncio

@injected
def email_service(smtp_client, logger, /, recipient: str, message: str):
    logger.info(f"Sending email to {recipient}")
    return smtp_client.send(recipient, message)

# Use the DI system properly
def main():
    design = Design()
    # Configure your dependencies
    design.bind(smtp_client, to=SMTPClient())
    design.bind(logger, to=Logger())
    
    # Run through DI system
    asyncio.run(design.run(email_service, "user@example.com", "Hello"))
```

## Suppressing the Rule

In cases where you need to call an `@injected` function directly (e.g., testing, migration, special entry points), you can suppress this rule using one of these methods:

### Method 1: Explicit Marking (Preferred)
```python
result = injected_function(args)  # pinjected: explicit-call
```

This clearly indicates that the direct call is intentional and understood.

### Method 2: Standard noqa
```python
result = injected_function(args)  # noqa: PINJ042
```

### Method 3: Explanation Comment
```python
# Direct call needed for backwards compatibility
result = injected_function(args)  # pinjected: explicit-call - legacy API
```

## Common Scenarios

### Testing
```python
def test_service():
    # Testing often requires direct calls
    result = my_service("test")  # pinjected: explicit-call - unit test
    assert result == expected
```

### Main Entry Points
```python
if __name__ == "__main__":
    # Entry points may need direct calls before setting up DI
    initial_config = load_config()  # pinjected: explicit-call - bootstrap
```

### Migration Code
```python
# During migration from non-DI to DI architecture
def legacy_wrapper(data):
    # Temporary direct call during migration
    return new_injected_service(data)  # noqa: PINJ042 - migration phase
```

## Best Practices

1. **Prefer Dependency Injection**: Convert regular functions to `@injected` when they need injected dependencies
2. **Use @instance for Entry Points**: Entry points that need DI services should use `@instance`
3. **Document Intentional Calls**: When marking as intentional, add a comment explaining why
4. **Minimize Direct Calls**: Direct calls should be exceptional, not routine

## Configuration

This rule cannot be disabled globally as it catches a fundamental architectural violation. Use explicit markings for intentional exceptions.

## See Also

- PINJ009: No direct calls to @injected functions (within @injected contexts)
- [Pinjected Documentation - Dependency Injection](https://github.com/pinjected/pinjected)