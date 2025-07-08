# PINJ011: IProxy Type Annotations

## Overview

**Rule ID:** PINJ011  
**Category:** Typing  
**Severity:** Warning  
**Auto-fixable:** No

Variables holding references to `@instance` or `@injected` functions should use `IProxy[T]` type annotations.

## Rationale

The `IProxy[T]` type wrapper is used for:

1. **Unresolved References:** Variables that hold references to `@instance` or `@injected` functions before resolution
2. **Entry Points:** Variables used as entry points for `python -m pinjected run`
3. **Type Safety:** Distinguishes between IProxy references and resolved values

**Important:** Injected dependencies (parameters before `/` in `@injected` functions) should NOT use `IProxy[T]`. They receive resolved values, not IProxy objects.

## Rule Details

This rule currently checks:

1. **Instance Function Returns:** Entry point services may optionally return `IProxy[T]` (currently checking, but may be revised)

The rule does NOT check:
- Injected dependencies (parameters before `/`) - these should use their actual types

### Examples

✅ **Correct:** Injected dependencies use actual types, not IProxy
```python
from pinjected import injected, instance, IProxy

# CORRECT: Injected dependencies (before /) use their actual types
@injected
def process_order(
    order_service: OrderService,      # Correct: actual type
    payment_client: PaymentClient,    # Correct: actual type
    logger: Logger,                   # Correct: actual type
    /,
    order_id: str
) -> Order:
    # These are resolved values, not IProxy objects
    return order_service.process(order_id)

# Instance functions
@instance
def user_service() -> UserService:
    return UserService()

@instance
def database_client() -> DatabaseClient:
    return PostgresClient()
```

✅ **Correct:** IProxy for entry point variables
```python
from pinjected import instance, injected, IProxy

@instance
def database() -> Database:
    return PostgresDB()

@injected
def process_data(db: Database, /, data: str) -> Result:
    return db.process(data)

# IProxy for entry point variables
run_processor: IProxy[Result] = process_data("input.csv")  # Entry point
db_ref: IProxy[Database] = database  # Reference to @instance function
```

❌ **Incorrect:** Using IProxy for injected dependencies
```python
# WRONG: Injected dependencies should NOT use IProxy
@injected
def bad_example(
    service: IProxy[Service],    # Wrong! Should be: Service
    logger: IProxy[Logger],      # Wrong! Should be: Logger
    /,
    data: str
):
    pass
```

## Common Patterns and Best Practices

### 1. Entry Points and IProxy
```python
from pinjected import instance, injected, IProxy

@instance
def database() -> Database:
    return PostgresDB()

@injected
def process_report(
    db: Database,            # Correct: actual type for injected dependency
    logger: Logger,          # Correct: actual type
    /,
    report_id: str
) -> Report:
    return db.fetch_report(report_id)

# Entry points use IProxy
run_report: IProxy[Report] = process_report("monthly-2024")  # IProxy for entry point
db_instance: IProxy[Database] = database  # IProxy for @instance reference
```

### 2. Calling @injected functions from other @injected functions
```python
from typing import Protocol

class ReportProcessorProtocol(Protocol):
    def __call__(self, report_id: str) -> Report: ...

@injected
def generate_summary(
    process_report: ReportProcessorProtocol,  # Dependency uses Protocol, not IProxy
    formatter: Formatter,                     # Actual type
    /,
    report_id: str
) -> Summary:
    report = process_report(report_id)  # Building AST, not executing
    return formatter.summarize(report)
```

### 3. IProxy in module-level variables
```python
# Module-level entry points
from pinjected import instance, injected, IProxy

@instance
def app_config() -> Config:
    return Config.from_env()

@injected
def run_app(config: Config, /, args: List[str]) -> None:
    # Application logic
    pass

# Module-level IProxy variables for CLI execution
config_ref: IProxy[Config] = app_config
run_main: IProxy[None] = run_app(sys.argv[1:])
```

### 4. When NOT to use IProxy
```python
# ✅ Correct: No IProxy for injected dependencies
@injected
def process_data(
    processor: DataProcessor,     # Actual type, not IProxy
    validator: Validator,         # Actual type, not IProxy
    config: dict,                 # Plain data type
    /,
    data: List[str],             # Runtime parameter
    options: ProcessOptions       # Runtime parameter
) -> ProcessedData:
    # All parameters receive resolved values
    validated = validator.validate(data)
    return processor.process(validated, options)
```

## Current Rule Behavior

Currently, this rule only checks:
- Return types of `@instance` functions for service-type patterns

The rule was updated to NOT check:
- Injected dependencies (parameters before `/` in `@injected` functions)
- These should always use their actual types, never `IProxy[T]`

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

## Key Takeaways

1. **Injected dependencies (before `/`) should NEVER use `IProxy[T]`**
   - They receive resolved values, not IProxy objects
   - Use the actual type: `logger: Logger`, not `logger: IProxy[Logger]`

2. **Use `IProxy[T]` for:**
   - Variables holding references to `@instance` or `@injected` functions
   - Entry point variables for CLI execution
   - Module-level variables that will be resolved later

3. **Common correct patterns:**
   ```python
   # Injected dependency - NO IProxy
   @injected
   def process(logger: Logger, /, data: str): ...
   
   # Entry point variable - YES IProxy
   run_process: IProxy[Result] = process("input.txt")
   
   # Reference to @instance - YES IProxy
   db_ref: IProxy[Database] = database_instance
   ```

## Related Rules

- **PINJ008:** Injected dependency declaration
- **PINJ015:** Missing slash separator

## See Also

- [Pinjected IProxy documentation](https://pinjected.readthedocs.io/iproxy)
- [Type Safety in Dependency Injection](https://pinjected.readthedocs.io/type-safety)

## Version History

- **1.0.0:** Initial implementation