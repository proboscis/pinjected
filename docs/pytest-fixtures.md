# Pytest Fixtures from Pinjected Design

This document describes how to use pinjected's Design objects to automatically create pytest fixtures, allowing seamless integration between pinjected's dependency injection and pytest's fixture system.

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [How It Works](#how-it-works)
4. [Basic Usage](#basic-usage)
5. [Advanced Usage](#advanced-usage)
6. [API Reference](#api-reference)
7. [Limitations](#limitations)
8. [Best Practices](#best-practices)
9. [Examples](#examples)

## Overview

The `pinjected.test` module allows you to automatically generate pytest fixtures from a pinjected Design object. This enables you to:

- Use pinjected's dependency injection in your tests
- Automatically expose all bindings in a Design as pytest fixtures
- Maintain consistency between application dependencies and test fixtures
- Leverage pinjected's powerful binding and design composition features in tests

## Quick Start

```python
# In conftest.py or test file
from pinjected import design
from pinjected.test import register_fixtures_from_design

# Define your test design
test_design = design(
    database=database_connection,
    user_service=user_service,
    auth_service=auth_service,
)

# Register all bindings as fixtures
register_fixtures_from_design(test_design)

# Now use them in tests
@pytest.mark.asyncio
async def test_user_creation(user_service, database):
    user = await user_service.create_user("test@example.com")
    assert user.id in database
```

## How It Works

1. **Design Extraction**: The module extracts all bindings from your Design object
2. **Fixture Generation**: For each binding, it creates an async pytest fixture
3. **Shared Resolver**: Fixtures within the same pytest scope share a single AsyncResolver instance
4. **Async Resolution**: When a test requests a fixture, it's resolved using the shared resolver
5. **Automatic Registration**: Fixtures are registered in the calling module's namespace

### Architecture

```
Design Object → Binding Extraction → Fixture Factory → pytest Registration
     ↓                                      ↓
  Bindings                         Scoped AsyncResolver
                                  (shared within scope)
```

The key feature is that all fixtures within the same pytest scope (function, class, module, or session) share the same resolver instance, ensuring proper dependency sharing.

## Basic Usage

### Simple Design Registration

```python
from pinjected import design, injected
from pinjected.test import register_fixtures_from_design

# Define some services
@injected
def config_service():
    return {"api_key": "test-key", "debug": True}

@injected
def api_client(config):
    return APIClient(config["api_key"])

# Create design
test_design = design(
    config=config_service,
    api_client=api_client,
)

# Register fixtures
register_fixtures_from_design(test_design)

# Use in tests
@pytest.mark.asyncio
async def test_api_client(api_client, config):
    assert api_client.api_key == config["api_key"]
```

### Using the DesignFixtures Class Directly

For more control, you can use the `DesignFixtures` class:

```python
from pinjected.test import DesignFixtures

fixtures = DesignFixtures(test_design)
fixtures.register("database", scope="module")  # Module-scoped fixture
fixtures.register("cache", scope="session")     # Session-scoped fixture
```

## Class-Based Test Organization

### Using Fixtures in Test Classes

When organizing tests in classes, you have several options for integrating pinjected fixtures:

#### Option 1: Module-Level Registration (Recommended)

The simplest approach is to register fixtures at module level, which makes them available to all test classes:

```python
from pinjected import design
from pinjected.test import register_fixtures_from_design

# Module-level design
test_design = design(
    database=test_database,
    user_service=user_service,
)

# Register once for the entire module
register_fixtures_from_design(test_design)

class TestUserService:
    @pytest.mark.asyncio
    async def test_create_user(self, user_service, database):
        user = await user_service.create_user("test@example.com")
        assert user.id in database["users"]

class TestAuthService:
    @pytest.mark.asyncio
    async def test_login(self, auth_service, database):
        # Different class, same fixtures
        pass
```

#### Option 2: Class-Specific Designs (Proposed API)

⚠️ **NOTE: The following features are NOT YET IMPLEMENTED. They are proposed APIs for future development.**

For more control, we propose these APIs for class-specific fixture registration:

```python
from pinjected.test import add_fixtures_from_design, fixture_override

# Decorator approach (Primary API)
@add_fixtures_from_design(user_test_design, scope="class")
class TestUserService:
    @pytest.mark.asyncio
    async def test_create_user(self, user_service):
        # Fixtures from user_test_design
        pass

# Alternative: Class attribute approach
class TestAuthService:
    __pinjected_design__ = auth_test_design
    __pinjected_scope__ = "class"  # Optional, defaults to "function"
    
    @pytest.mark.asyncio
    async def test_login(self, auth_service):
        pass
```

#### Option 3: Inheritance-Based Design Composition

```python
# Base class with common fixtures
class BaseServiceTest:
    __pinjected_design__ = design(
        database=test_database,
        logger=test_logger,
    )

# Derived class adds more fixtures
class TestUserService(BaseServiceTest):
    __pinjected_design__ = BaseServiceTest.__pinjected_design__ + design(
        user_service=user_service,
        email_service=mock_email_service,
    )
    
    @pytest.mark.asyncio
    async def test_user_creation(self, user_service, database, logger):
        # Has access to base class fixtures too
        pass
```

#### Option 4: Per-Method Fixture Override

```python
from pinjected.test import fixture_override

class TestUserService:
    __pinjected_design__ = default_test_design
    
    @pytest.mark.asyncio
    async def test_normal_case(self, user_service):
        # Uses default design
        pass
    
    @pytest.mark.asyncio
    @fixture_override(user_service=special_user_service)
    async def test_special_case(self, user_service):
        # Uses overridden user_service
        pass
```

### Proposed Implementation Example

Here's how you might implement the class-based fixture registration in your test code:

```python
# In your test file
from pinjected import design
from pinjected.test import add_fixtures_from_design

# Define test-specific designs
user_test_design = design(
    database=in_memory_database,
    user_service=user_service,
    email_service=mock_email_service,
)

admin_test_design = user_test_design + design(
    admin_service=admin_service,
    permissions=test_permissions,
)

@add_fixtures_from_design(user_test_design)
class TestUserRegistration:
    """Test user registration flow."""
    
    @pytest.mark.asyncio
    async def test_register_new_user(self, user_service, email_service, database):
        # Register user
        user = await user_service.register("new@example.com", "password")
        
        # Verify in database
        assert user.email in database["users"]
        
        # Verify email sent
        assert len(email_service.sent_emails) == 1
    
    @pytest.mark.asyncio
    async def test_register_duplicate_user(self, user_service, database):
        # First registration
        await user_service.register("user@example.com", "password")
        
        # Duplicate should fail
        with pytest.raises(UserAlreadyExistsError):
            await user_service.register("user@example.com", "password")

@add_fixtures_from_design(admin_test_design, scope="class")
class TestAdminFeatures:
    """Test admin-specific features."""
    
    @pytest.mark.asyncio
    async def test_admin_can_delete_user(self, admin_service, user_service, database):
        # Create user
        user = await user_service.register("user@example.com", "password")
        
        # Admin deletes user
        await admin_service.delete_user(user.id)
        
        # Verify deleted
        assert user.id not in database["users"]
    
    @pytest.mark.asyncio
    async def test_admin_permissions(self, admin_service, permissions):
        assert permissions.can_delete_users is True
        assert permissions.can_modify_settings is True
```

### Benefits of Class-Based Organization

1. **Better Organization**: Group related tests with their specific dependencies
2. **Reduced Boilerplate**: Define design once per class instead of importing in each test
3. **Inheritance Support**: Base test classes can provide common fixtures
4. **Scoping Control**: Easy to set class-level scope for expensive fixtures
5. **Override Flexibility**: Can override specific fixtures for specific test methods

### Implementation Status

⚠️ **IMPORTANT**: The class-based APIs (`@add_fixtures_from_design`, `__pinjected_design__`, `@fixture_override`) are **proposed features and NOT YET IMPLEMENTED**. 

Currently, you should use module-level registration (Option 1) for class-based tests. These proposed APIs are included in the documentation as a reference for future development and to gather community feedback.

Here's a potential implementation approach for `@add_fixtures_from_design`:

```python
# Proposed implementation (not yet available)
def add_fixtures_from_design(design_obj, scope="function", exclude=None):
    """Decorator to add fixtures from a design to a test class."""
    def decorator(cls):
        # Register fixtures in the module where the class is defined
        module = sys.modules[cls.__module__]
        fixtures = DesignFixtures(design_obj)
        fixtures.caller_module = module
        
        # Register all fixtures with specified scope
        fixtures.register_all(
            scope=scope,
            exclude=exclude
        )
        
        # Store reference on class for introspection
        cls._pinjected_fixtures = fixtures
        return cls
    
    return decorator
```

To implement similar functionality today, you can:

```python
# Current approach - module level registration with class organization
from pinjected import design
from pinjected.test import register_fixtures_from_design

# Define class-specific designs with unique binding names
user_test_design = design(
    user_database=in_memory_database,
    user_service=user_service_impl,
)

admin_test_design = design(
    admin_database=admin_database,
    admin_service=admin_service_impl,
    admin_permissions=admin_permissions_impl,
)

# Register fixtures
register_fixtures_from_design(user_test_design, scope="class")
register_fixtures_from_design(admin_test_design, scope="class")

class TestUserService:
    @pytest.mark.asyncio
    async def test_create(self, user_service, user_database):
        # Use fixtures with unique names
        pass

class TestAdminService:
    @pytest.mark.asyncio
    async def test_admin(self, admin_service, admin_permissions):
        # Use fixtures with unique names
        pass
```

## Advanced Usage

### Fixture Options

The `register_fixtures_from_design` function supports several options:

```python
register_fixtures_from_design(
    test_design,
    scope="function",        # Fixture scope: function, class, module, session
    include={"service_a"},   # Only register these bindings
    exclude={"logger"}       # Exclude these bindings
)
```

**Note**: The `prefix` parameter shown in some examples is not currently implemented. To avoid naming conflicts, consider using unique binding names in your Design objects.

### Scoped Fixtures

Control fixture lifecycle with pytest scopes:

```python
# Function scope (default) - new instance per test
register_fixtures_from_design(test_design, scope="function")

# Class scope - shared within test class
register_fixtures_from_design(test_design, scope="class")

# Module scope - shared within module
register_fixtures_from_design(test_design, scope="module")

# Session scope - shared across entire test session
register_fixtures_from_design(test_design, scope="session")
```

### Filtering Fixtures

Include or exclude specific bindings:

```python
# Only register specific fixtures
register_fixtures_from_design(
    test_design,
    include={"database", "cache", "user_service"}
)

# Exclude certain fixtures
register_fixtures_from_design(
    test_design,
    exclude={"logger", "debug_tools"}
)
```

### Avoiding Naming Conflicts

**Note**: The `prefix` parameter is not currently implemented. To avoid naming conflicts, consider these approaches:

1. Use unique binding names in your Design objects:
```python
test_design = design(
    test_database=test_database_impl,
    test_cache=test_cache_impl,
)

# Usage
@pytest.mark.asyncio
async def test_something(test_database, test_cache):
    pass
```

2. Use separate Design objects with different binding names for different test modules.

## API Reference

### `register_fixtures_from_design`

```python
def register_fixtures_from_design(
    design_obj: Union[Design, DelegatedVar[Design]],
    scope: str = 'function',
    include: Optional[Set[str]] = None,
    exclude: Optional[Set[str]] = None
) -> DesignFixtures:
```

**Parameters:**
- `design_obj`: The pinjected Design object containing bindings
- `scope`: Pytest fixture scope ('function', 'class', 'module', 'session')
- `include`: Set of binding names to include (if provided, only these are registered)
- `exclude`: Set of binding names to exclude from registration

**Returns:**
- `DesignFixtures` instance (for advanced use cases)

### `DesignFixtures` Class

```python
class DesignFixtures:
    def __init__(self, design_obj: Union[Design, DelegatedVar[Design]], caller_file: Optional[str] = None)
    
    def register(
        self,
        binding_name: str,
        scope: str = 'function',
        fixture_name: Optional[str] = None
    ) -> None
    
    def register_all(
        self,
        scope: str = 'function',
        include: Optional[Set[str]] = None,
        exclude: Optional[Set[str]] = None
    ) -> None
```

## Limitations

### Shared State Within Scopes

Fixtures within the same pytest scope share the same resolver instance, which means dependencies are properly shared:

```python
# Dependencies ARE shared within the same scope
@injected
def shared_state():
    return {"id": random.randint(1000, 9999)}

@injected
def service_a(shared_state):
    return {"service": "a", "state_id": shared_state["id"]}

@injected
def service_b(shared_state):
    return {"service": "b", "state_id": shared_state["id"]}

# In test: service_a and service_b will have the SAME state_id value
# when used as fixtures in the same test (function scope)
```

However, fixtures in different scopes will have different resolver instances and won't share state.

### Cross-Scope Sharing

If you need to share state across different scopes (e.g., between function-scoped and module-scoped fixtures), you can:

1. **Use Higher Scope**: Register all related fixtures with the same higher scope (e.g., module or session)
```python
register_fixtures_from_design(test_design, scope="module")
```

2. **Use Pytest's Native Fixtures**: For cross-scope dependencies
```python
@pytest.fixture(scope="session")
def shared_value():
    return random.randint(1000, 9999)

@pytest.mark.asyncio
async def test_something(database, shared_value):
    # database from pinjected, shared_value from pytest
    pass
```

### Other Limitations

- All fixtures are **async** and require `@pytest.mark.asyncio`
- Handler configuration (from `add()`) is not preserved during pickling
- DelegatedVar designs may not expose bindings until resolved

## Best Practices

### 1. Use in conftest.py

Register fixtures in `conftest.py` for test-wide availability:

```python
# conftest.py
from pinjected.test import register_fixtures_from_design
from myapp.test_utils import test_design

register_fixtures_from_design(test_design)
```

### 2. Separate Test and Production Designs

```python
# test_design.py
from pinjected import design
from myapp.design import production_design

# Override production bindings for testing
test_overrides = design(
    database=test_database,
    email_service=mock_email_service,
)

test_design = production_design + test_overrides
```

### 3. Use Appropriate Scopes

- `function` (default): For isolated tests
- `class`: For related tests in a class
- `module`: For expensive resources used across a module
- `session`: For very expensive resources (e.g., database setup)

### 4. Document Fixture Dependencies

```python
@pytest.mark.asyncio
async def test_user_service(
    user_service,    # From pinjected design
    database,        # From pinjected design
    test_user,       # Regular pytest fixture
):
    """Test user service.
    
    Fixtures:
        user_service: User service with mocked dependencies
        database: Test database instance
        test_user: Pytest fixture providing test user data
    """
    pass
```

## Examples

### Complete Example: Testing a Web Application

```python
# test_design.py
from pinjected import design, injected
from myapp.services import UserService, AuthService, EmailService

# Test implementations
@injected
def test_database():
    """In-memory test database."""
    return {"users": {}, "sessions": {}}

@injected
def mock_email_service():
    """Mock email service that records sent emails."""
    sent_emails = []
    
    class MockEmailService:
        def send(self, to, subject, body):
            sent_emails.append({"to": to, "subject": subject, "body": body})
        
        def get_sent_emails(self):
            return sent_emails
    
    return MockEmailService()

# Create test design
test_design = design(
    database=test_database,
    email_service=mock_email_service,
    user_service=UserService,
    auth_service=AuthService,
)

# conftest.py
from pinjected.test import register_fixtures_from_design
from .test_design import test_design

# Register all fixtures from the design
register_fixtures_from_design(test_design)

# test_user_service.py
import pytest

@pytest.mark.asyncio
async def test_user_registration(user_service, email_service, database):
    # Register a user
    user = await user_service.register("user@example.com", "password")
    
    # Check user in database
    assert user.id in database["users"]
    
    # Check welcome email was sent
    emails = email_service.get_sent_emails()
    assert len(emails) == 1
    assert emails[0]["to"] == "user@example.com"
    assert "Welcome" in emails[0]["subject"]

@pytest.mark.asyncio
async def test_user_login(auth_service, user_service, database):
    # Create user first
    await user_service.register("user@example.com", "password")
    
    # Test login
    session = await auth_service.login("user@example.com", "password")
    assert session.user_email == "user@example.com"
    assert session.id in database["sessions"]
```

### Example: Testing with Mixed Fixtures

```python
# Mix pinjected fixtures with regular pytest fixtures
@pytest.fixture
def sample_data():
    return {"id": 123, "name": "Test"}

@pytest.mark.asyncio  
async def test_mixed_fixtures(database, user_service, sample_data):
    # database and user_service from pinjected
    # sample_data from regular pytest
    user = await user_service.create_user(sample_data["name"])
    assert user.name == sample_data["name"]
```

### Example: Module-Scoped Database

```python
# For expensive resources, use module or session scope
database_design = design(
    database=expensive_database_setup
)

register_fixtures_from_design(
    database_design,
    scope="module",  # Shared across all tests in module
    include={"database"}  # Only register database fixture
)
```

## Troubleshooting

### "Fixture not found" Error

Ensure fixtures are registered before tests run:
- Place registration in `conftest.py`
- Or at module level in test file

### "Event loop is closed" Error

Make sure to use `@pytest.mark.asyncio` decorator:
```python
@pytest.mark.asyncio  # Required!
async def test_something(my_fixture):
    pass
```

### Fixtures Not Sharing State

This is by design - each fixture gets its own resolver. Use one of the workarounds mentioned in the Limitations section.

## Implementation Details

The pytest fixtures functionality is implemented in `pinjected/pytest_fixtures.py` and re-exported through `pinjected.test` for convenience. The main components are:

- `DesignFixtures`: The core class that handles fixture creation and registration
- `register_fixtures_from_design`: Convenience function for simple registration
- `AsyncResolver`: Used internally to resolve dependencies asynchronously

## Future Development

The class-based fixture registration APIs (`@add_fixtures_from_design`, etc.) are planned features. If you're interested in:

- Contributing to the implementation
- Following development progress
- Suggesting improvements to the API

Please check the pinjected GitHub repository issues and discussions.

## Conclusion

The pytest fixtures integration provides a powerful way to use pinjected's dependency injection in your tests. While it has some limitations around shared state, it excels at providing clean, isolated test fixtures that mirror your production dependency structure.

The current module-level registration approach works well for most use cases, and the planned class-based APIs will provide even more flexibility for organizing test fixtures in the future.