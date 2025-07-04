# PINJ011: IProxy Type Annotations

## Overview

**Rule ID:** PINJ011  
**Category:** Typing  
**Severity:** Warning  
**Auto-fixable:** No

Dependencies in Pinjected should use `IProxy[T]` type annotations for proper type checking and clarity.

## Rationale

The `IProxy[T]` type wrapper is essential for Pinjected's type system because it:

1. **Type Safety:** Enables proper type checking for dependencies
2. **Clear Boundaries:** Distinguishes injected dependencies from runtime values
3. **IDE Support:** Provides better autocomplete and type hints
4. **Documentation:** Makes dependency injection patterns explicit
5. **Runtime Safety:** Helps prevent mixing injected and non-injected values

## Rule Details

This rule checks for proper `IProxy[T]` usage in two contexts:

1. **Injected Function Parameters:** Service-type dependencies should be annotated with `IProxy[T]`
2. **Instance Function Returns:** Entry point services should return `IProxy[T]`

The rule identifies service types by common naming patterns (Service, Client, Repository, Manager, etc.).

### Examples of Violations

❌ **Bad:** Missing IProxy annotations
```python
from pinjected import injected, instance

# Error: Service-type parameters without IProxy
@injected
def process_order(
    order_service: OrderService,      # Should be IProxy[OrderService]
    payment_client: PaymentClient,    # Should be IProxy[PaymentClient]
    logger: Logger,                   # Should be IProxy[Logger]
    /,
    order_id: str
):
    return order_service.process(order_id)

# Error: Instance function returning service without IProxy
@instance
def user_service() -> UserService:  # Should be IProxy[UserService]
    return UserService()

@instance
def database_client() -> DatabaseClient:  # Should be IProxy[DatabaseClient]
    return PostgresClient()
```

✅ **Good:** Proper IProxy annotations
```python
from pinjected import injected, instance, IProxy

# Good: Service-type parameters with IProxy
@injected
def process_order(
    order_service: IProxy[OrderService],
    payment_client: IProxy[PaymentClient],
    logger: IProxy[Logger],
    /,
    order_id: str
):
    return order_service.process(order_id)

# Good: Instance functions returning IProxy
@instance
def user_service() -> IProxy[UserService]:
    return UserService()

@instance
def database_client() -> IProxy[DatabaseClient]:
    return PostgresClient()
```

## Common Patterns and Best Practices

### 1. Annotate all service dependencies
```python
# ❌ Bad - mixed annotations
@injected
def create_report(
    report_service: ReportService,      # Missing IProxy
    db: IProxy[Database],               # Has IProxy
    cache: CacheManager,                # Missing IProxy
    /,
    report_type: str
):
    pass

# ✅ Good - consistent IProxy usage
@injected
def create_report(
    report_service: IProxy[ReportService],
    db: IProxy[Database],
    cache: IProxy[CacheManager],
    /,
    report_type: str
):
    pass
```

### 2. Entry point services should return IProxy
```python
# ❌ Bad - entry points without IProxy
@instance
def api_gateway() -> APIGateway:
    return APIGateway()

@instance
def auth_handler() -> AuthHandler:
    return OAuthHandler()

# ✅ Good - entry points with IProxy
@instance
def api_gateway() -> IProxy[APIGateway]:
    return APIGateway()

@instance
def auth_handler() -> IProxy[AuthHandler]:
    return OAuthHandler()
```

### 3. Non-service types don't need IProxy
```python
# ✅ Good - IProxy only for services
@injected
def process_data(
    processor: IProxy[DataProcessor],    # Service: needs IProxy
    validator: IProxy[Validator],        # Service: needs IProxy
    config: dict,                        # Data: no IProxy needed
    /,
    data: List[str],                     # Runtime param: no IProxy
    options: ProcessOptions              # Value object: no IProxy
):
    # Simple types, primitives, and value objects don't need IProxy
    pass
```

### 4. Complex service hierarchies
```python
# ✅ Good - IProxy with generic types
@injected
def handle_request(
    router: IProxy[Router[Request, Response]],
    middleware: IProxy[List[Middleware]],
    auth: IProxy[Optional[AuthService]],
    /,
    request: Request
) -> Response:
    # IProxy works with generic types
    if auth:
        auth.validate(request)
    
    for mw in middleware:
        request = mw.process(request)
    
    return router.route(request)
```

### 5. Factory patterns with IProxy
```python
# ✅ Good - factories returning IProxy
@instance
def service_factory() -> IProxy[ServiceFactory]:
    return ServiceFactory()

@injected
def create_handler(
    factory: IProxy[ServiceFactory],
    /,
    handler_type: str
) -> IProxy[Handler]:
    # Factory creates handlers that are also IProxy-wrapped
    return factory.create_handler(handler_type)
```

## Service Type Detection

The rule identifies service types by these patterns in type names:
- Service
- Client
- Repository
- Manager
- Factory
- Provider
- Handler
- Processor
- Validator
- Logger
- Database
- Cache
- Gateway
- Controller

Types without these patterns won't trigger the rule:
```python
@injected
def calculate(
    calculator: Calculator,  # Has none of the patterns - no warning
    config: Config,          # Simple config - no warning
    utils: Utils,            # Utilities - no warning
    /,
    value: float
):
    pass
```

## Configuration

This rule has no configuration options.

## When to Disable

You might want to disable this rule if:
- You're migrating legacy code gradually
- You have a different type annotation strategy
- You're using a custom dependency injection wrapper

To disable for a specific function:
```python
# noqa: PINJ011
@injected
def legacy_function(order_service: OrderService, /, order_id: str):
    # Will add IProxy in next refactor
    pass
```

To disable in configuration:
```toml
[tool.pinjected-linter]
disable = ["PINJ011"]
```

## Migration Guide

When adding IProxy to existing code:

```python
# Step 1: Import IProxy
from pinjected import IProxy

# Step 2: Update function signatures
# Before:
@injected
def process(service: UserService, /, data: dict):
    pass

# After:
@injected
def process(service: IProxy[UserService], /, data: dict):
    pass

# Step 3: Update instance functions
# Before:
@instance
def user_service() -> UserService:
    return UserService()

# After:
@instance
def user_service() -> IProxy[UserService]:
    return UserService()
```

## Related Rules

- **PINJ008:** Injected dependency declaration
- **PINJ015:** Missing slash separator

## See Also

- [Pinjected IProxy documentation](https://pinjected.readthedocs.io/iproxy)
- [Type Safety in Dependency Injection](https://pinjected.readthedocs.io/type-safety)

## Version History

- **1.0.0:** Initial implementation