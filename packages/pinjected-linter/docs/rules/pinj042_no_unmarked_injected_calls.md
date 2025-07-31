# PINJ042: No Unmarked Calls to @injected Functions

## Overview

This rule forbids calling `@injected` functions from non-`@injected` contexts without explicitly marking the call as intentional. `@injected` functions are designed to be used through the dependency injection system, and direct calls bypass the entire DI framework.

**Exception**: Module-level calls to create IProxy entrypoints are allowed when explicitly typed as `IProxy[T]` with a type parameter.

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

# Module-level call without IProxy type annotation
# ERROR: Module-level calls must be typed as IProxy[T]
default_emailer = email_service("default@example.com", "Default")

# Module-level call with bare IProxy (no type parameter)
# ERROR: IProxy must have a type parameter
typed_emailer: IProxy = email_service("typed@example.com", "Typed")
```

### ✅ Correct - Option 1: Use Dependency Injection (Recommended)

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

### ✅ Correct - Option 2: Use Pytest Fixtures (For Tests)

When writing pytest tests, dependencies should be requested as fixtures:

```python
from pinjected import injected, design
from pinjected.test import register_fixtures_from_design

@injected
def email_service(smtp_client, logger, /, recipient: str, message: str):
    logger.info(f"Sending email to {recipient}")
    return smtp_client.send(recipient, message)

@injected
def database_service(connection, /):
    return connection

# At module level: Set up test design
test_design = design(
    email_service=email_service(),
    database_service=database_service(),
    smtp_client=MockSMTPClient(),
    logger=MockLogger(),
    connection=MockConnection()
)
register_fixtures_from_design(test_design)

# In test functions: Use as fixtures
def test_email_sending(email_service, database_service):
    # CORRECT: email_service is the resolved function, not an IProxy
    result = email_service("test@example.com", "Test message")
    assert result.success
    
    # Can use multiple fixtures
    db_result = database_service.query("SELECT * FROM emails")
    assert len(db_result) > 0

@pytest.mark.asyncio
async def test_async_service(email_service):
    # Works with async tests too
    result = await email_service.send_async("test@example.com", "Async test")
    assert result.delivered
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

### ✅ Correct - Option 4: Module-Level IProxy Entrypoints

Module-level calls to `@injected` functions are allowed when creating IProxy entrypoints, but **only when explicitly typed as `IProxy[T]` with a type parameter**:

```python
from pinjected import injected, IProxy
from typing import Any

@injected
def database_service(connection_pool, logger, /, query: str):
    logger.info(f"Executing query: {query}")
    return connection_pool.execute(query)

@injected
def api_handler(auth_service, db_service, /):
    async def handle(request):
        # Handler implementation
        pass
    return handle

# CORRECT: Module-level IProxy entrypoints with type parameters
# These create dependency injection entry points for the module
user_query_service: IProxy[DatabaseService] = database_service("SELECT * FROM users")
admin_api: IProxy[ApiHandler] = api_handler()

# Use Any if the specific type is unknown or dynamic
dynamic_service: IProxy[Any] = database_service("config")

# Also valid with qualified names
import pinjected
my_service: pinjected.IProxy[ServiceType] = api_handler()
```

This pattern is commonly used to:
- Define module-level entry points for dependency injection
- Create reusable IProxy instances that can be imported by other modules
- Set up application-wide service configurations

**Important**: The `IProxy[T]` type annotation with a type parameter is mandatory for module-level calls. This ensures:
- You understand you're creating an IProxy object, not executing the function
- Proper type checking for dependency resolution
- Clear documentation of expected return types

## Suppressing the Rule (NOT RECOMMENDED)

⚠️ **WARNING**: While you can suppress this rule, doing so is PROBABLY WRONG and should NOT be done without supervisor's instruction. The `# pinjected: explicit-call` comment is a complex feature that bypasses the dependency injection system and can lead to runtime errors.

**Before suppressing this rule, consider:**
1. Can you refactor to use proper dependency injection?
2. For tests, can you use pytest fixtures with `register_fixtures_from_design()`?
3. Can you use `Design().run()` to properly resolve dependencies?

If you absolutely must suppress (rare cases like legacy code migration):

### Method 1: Explicit Marking (Use With Extreme Caution)
```python
# ⚠️ DANGEROUS: Only use with supervisor approval
result = injected_function(args)  # pinjected: explicit-call
```

### Method 2: Standard noqa (Also Requires Justification)
```python
# ⚠️ Bypassing DI system - approved by [supervisor name]
result = injected_function(args)  # noqa: PINJ042
```

**Remember**: These suppressions bypass the entire dependency injection system. The function's dependencies will NOT be resolved, and you'll get an IProxy object instead of the actual function result.

## Common Scenarios

### Testing (Use Pytest Fixtures Instead)
```python
# ❌ WRONG: Direct call in test
def test_service():
    result = my_service("test")  # pinjected: explicit-call
    assert result == expected

# ✅ CORRECT: Use pytest fixtures
def test_service(my_service):  # my_service injected as fixture
    result = my_service("test")
    assert result == expected
```

### Main Entry Points (Use Design Instead)
```python
# ❌ WRONG: Direct call in main
if __name__ == "__main__":
    initial_config = load_config()  # pinjected: explicit-call

# ✅ CORRECT: Use Design for entry points
if __name__ == "__main__":
    design = Design()
    # Configure dependencies
    asyncio.run(design.run(load_config))
```

### Migration Code (Requires Approval)
```python
# ⚠️ Only during approved migration phase
# TODO: Remove after migration to DI (ticket #12345)
def legacy_wrapper(data):
    # Temporary - approved by [supervisor name]
    return new_injected_service(data)  # noqa: PINJ042
```

## Best Practices

1. **Always Use Dependency Injection**: Convert regular functions to `@injected` when they need injected dependencies
2. **Use Pytest Fixtures for Tests**: Use `register_fixtures_from_design()` instead of direct calls in tests
3. **Use @instance for Entry Points**: Entry points that need DI services should use `@instance`
4. **Avoid explicit-call**: The `# pinjected: explicit-call` comment is probably wrong - seek supervisor approval first
5. **No Direct Calls**: Direct calls to `@injected` functions should be eliminated, not suppressed

## Configuration

This rule cannot be disabled globally as it catches a fundamental architectural violation. Use explicit markings for intentional exceptions.

## See Also

- PINJ009: No direct calls to @injected functions (within @injected contexts)
- [Pinjected Documentation - Dependency Injection](https://github.com/pinjected/pinjected)