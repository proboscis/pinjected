# PINJ014: Missing .pyi Stub File

## Overview

**Rule ID:** PINJ014  
**Category:** Documentation  
**Severity:** Warning  
**Auto-fixable:** No

Modules containing `@injected` functions should have corresponding `.pyi` stub files for better IDE support and type checking.

## Rationale

Type stub files (`.pyi`) are crucial for Pinjected modules because:

1. **IDE Support:** Provides better autocomplete and navigation for `@injected` functions
2. **Type Checking:** Enables proper type checking with dependency injection patterns
3. **Documentation:** Serves as interface documentation for modules
4. **Editor Integration:** Improves code intelligence in editors that don't fully understand decorators
5. **API Clarity:** Makes the public API of modules explicit

## Rule Details

This rule checks if modules containing `@injected` functions have corresponding `.pyi` stub files. The rule is configurable and can:
- Set a minimum number of `@injected` functions to trigger the rule
- Search for stub files in multiple locations
- Ignore certain file patterns (like tests)

### Examples of Violations

❌ **Bad:** Module with @injected functions but no stub file
```python
# File: services/user_service.py
from pinjected import injected, IProxy

@injected
def get_user(
    database: IProxy[Database],
    cache: IProxy[Cache],
    /,
    user_id: str
) -> User:
    # Implementation...
    pass

@injected
async def a_create_user(
    database: IProxy[Database],
    validator: IProxy[Validator],
    /,
    user_data: dict
) -> User:
    # Implementation...
    pass

# Warning: No services/user_service.pyi found
```

✅ **Good:** Module with corresponding stub file
```python
# File: services/user_service.py
from pinjected import injected, IProxy

@injected
def get_user(
    database: IProxy[Database],
    cache: IProxy[Cache],
    /,
    user_id: str
) -> User:
    # Implementation...
    pass

# File: services/user_service.pyi
from typing import Any
from pinjected import injected, IProxy
from .models import User

@injected
def get_user(
    database: IProxy[Database],
    cache: IProxy[Cache],
    /,
    user_id: str
) -> User: ...

@injected
async def a_create_user(
    database: IProxy[Database],
    validator: IProxy[Validator],
    /,
    user_data: dict
) -> User: ...
```

## Stub File Content Guidelines

### 1. Basic stub structure
```python
# mymodule.pyi
from typing import Any, List, Optional
from pinjected import injected, IProxy

# Import necessary types
from .database import Database
from .models import User, Order

# Copy function signatures with @injected decorator
@injected
def process_order(
    database: IProxy[Database],
    logger: IProxy[Logger],
    /,
    order_id: str
) -> Order: ...

@injected
async def a_fetch_users(
    database: IProxy[Database],
    /,
    filter: Optional[dict] = None
) -> List[User]: ...
```

### 2. Include all public @injected functions
```python
# services/payment.pyi
from pinjected import injected, IProxy
from typing import Decimal

# Public API functions
@injected
def process_payment(
    payment_gateway: IProxy[PaymentGateway],
    fraud_detector: IProxy[FraudDetector],
    logger: IProxy[Logger],
    /,
    amount: Decimal,
    customer_id: str
) -> PaymentResult: ...

@injected
def refund_payment(
    payment_gateway: IProxy[PaymentGateway],
    logger: IProxy[Logger],
    /,
    transaction_id: str,
    amount: Optional[Decimal] = None
) -> RefundResult: ...

# Don't include private functions
# _internal_helper is not included in stub
```

### 3. Preserve type annotations
```python
# repository/user_repo.pyi
from typing import List, Optional, Dict, Any
from pinjected import injected, IProxy
from datetime import datetime

@injected
def find_users(
    database: IProxy[Database],
    /,
    filters: Dict[str, Any],
    limit: int = 100,
    offset: int = 0
) -> List[User]: ...

@injected
def get_user_by_id(
    database: IProxy[Database],
    cache: IProxy[Cache],
    /,
    user_id: str,
    include_deleted: bool = False
) -> Optional[User]: ...
```

## Configuration

Configure this rule in your `pyproject.toml`:

```toml
[tool.pinjected-linter.rules.PINJ014]
# Minimum number of @injected functions to require stub file (default: 1)
min_injected_functions = 2

# Additional directories to search for stub files (default: ["stubs", "typings"])
stub_search_paths = ["stubs", "typings", "types"]

# File patterns to ignore (default: ["**/tests/**", "**/migrations/**"])
ignore_patterns = [
    "**/tests/**",
    "**/test_*.py",
    "**/migrations/**",
    "**/scripts/**"
]
```

## Stub File Locations

The rule searches for stub files in this order:
1. Same directory as the module (e.g., `module.pyi` next to `module.py`)
2. In configured stub directories (e.g., `stubs/module.pyi`)
3. In `typings/` directory
4. Custom paths from `stub_search_paths` configuration

## When to Disable

You might want to disable this rule for:
- Small utility modules with few `@injected` functions
- Internal modules not part of public API
- Modules under active development

To disable for a specific module:
```python
# mypy: ignore-errors
# pinjected-linter: disable=PINJ014

from pinjected import injected

@injected
def internal_function(service, /, data):
    # Internal module, no stub needed
    pass
```

To disable in configuration:
```toml
[tool.pinjected-linter]
disable = ["PINJ014"]
```

## Benefits of Stub Files

1. **Better IDE Experience:**
   - Autocomplete works correctly with `@injected` functions
   - Go-to-definition navigates to stub signatures
   - Parameter hints show proper types

2. **Type Checking:**
   - mypy and other type checkers understand the interface
   - Catches type errors at development time
   - Documents expected types clearly

3. **API Documentation:**
   - Stub files serve as concise API documentation
   - Easy to see all public functions at a glance
   - Clear separation of interface from implementation

## Generating Stub Files

You can manually create stub files or use tools:

```bash
# Manual creation
touch services/user_service.pyi

# Use stubgen (from mypy)
stubgen services/user_service.py

# Then edit to add @injected decorators and proper types
```

## Related Rules

- **PINJ011:** IProxy type annotations (ensures proper typing)
- **PINJ008:** Injected dependency declaration

## See Also

- [PEP 484 - Stub Files](https://www.python.org/dev/peps/pep-0484/#stub-files)
- [mypy Stub Files Documentation](https://mypy.readthedocs.io/en/stable/stubs.html)
- [Pinjected Type Safety Guide](https://pinjected.readthedocs.io/type-safety)

## Version History

- **1.0.0:** Initial implementation with configurable options