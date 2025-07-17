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
6. **User-Facing Interface:** Shows only the runtime arguments that users need to provide

## Rule Details

This rule checks if modules containing `@injected` functions have corresponding `.pyi` stub files. The rule:
- Generates stub files with `@overload` decorators showing only runtime arguments
- Omits injected dependencies (everything before `/`) from the stub signatures
- Maintains original return types without transformation
- **Validates existing stub files to ensure signatures match expected format**
- Reports mismatches between actual and expected signatures
- Can be configured to require stubs only after a minimum number of `@injected` functions

### Examples of Violations

❌ **Bad:** Module with @injected functions but no stub file
```python
# File: services/user_service.py
from pinjected import injected, IProxy
from typing import Protocol

class UserFetcherProtocol(Protocol):
    def __call__(self, user_id: str) -> User: ...

@injected(protocol=UserFetcherProtocol)
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

❌ **Bad:** Stub file with incorrect signatures
```python
# File: services/user_service.py
from pinjected import injected, IProxy
from .models import User

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
from typing import overload
from .models import User

# INCORRECT: Shows injected dependencies
@overload
def get_user(database: IProxy[Database], cache: IProxy[Cache], user_id: str) -> User: ...

# Warning: Stub file services/user_service.pyi has incorrect signatures:
# Function 'get_user' has incorrect signature in stub file.
# Expected: def get_user(user_id: str) -> User
# Actual: def get_user(database: IProxy[Database], cache: IProxy[Cache], user_id: str) -> User
```

✅ **Good:** Module with corresponding stub file using @overload
```python
# File: services/user_service.py
from pinjected import injected, IProxy
from typing import Protocol
from .models import User

class UserFetcherProtocol(Protocol):
    def __call__(self, user_id: str) -> User: ...

@injected(protocol=UserFetcherProtocol)
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

# File: services/user_service.pyi
from typing import overload
from .models import User

# Note: @overload decorator shows only runtime arguments
@overload
def get_user(user_id: str) -> User: ...

@overload
async def a_create_user(user_data: dict) -> User: ...
```

## Stub File Content Guidelines

### Important: Use @overload for User-Facing Interface

**All `@injected` functions must use `@overload` in stub files.** This shows only the runtime arguments that users provide when calling the function, omitting the injected dependencies.

Key principles:
- Use `from typing import overload`
- Show only arguments after `/` (runtime arguments)
- Keep original return types (no transformation)
- Omit injected dependencies from signatures

### 1. Basic stub structure
```python
# mymodule.pyi
from typing import overload, List, Optional
from .models import User, Order

# Use @overload to show user-facing signatures
@overload
def process_order(order_id: str) -> Order: ...

@overload
async def a_fetch_users(filter: Optional[dict] = None) -> List[User]: ...
```

### 2. Functions with multiple runtime arguments
```python
# services/payment.py
from pinjected import injected
from typing import Decimal, Optional

@injected
def process_payment(
    payment_gateway: IProxy[PaymentGateway],
    fraud_detector: IProxy[FraudDetector],
    logger: IProxy[Logger],
    /,
    amount: Decimal,
    customer_id: str,
    *, 
    currency: str = "USD",
    metadata: Optional[dict] = None
) -> PaymentResult:
    # Implementation
    pass

# services/payment.pyi
from typing import overload, Decimal, Optional
from .models import PaymentResult

# Show all runtime arguments in the @overload signature
@overload
def process_payment(
    amount: Decimal,
    customer_id: str,
    *,
    currency: str = "USD",
    metadata: Optional[dict] = None
) -> PaymentResult: ...
```

### 3. Multiple overloads for different call patterns
```python
# repository/user_repo.py
from pinjected import injected
from typing import List, Optional, Dict, Any, Literal

@injected
def find_users(
    database: IProxy[Database],
    /,
    filters: Dict[str, Any] | None = None,
    *,
    limit: int = 100,
    offset: int = 0,
    format: Literal["json", "dataframe"] = "json"
) -> List[User] | pd.DataFrame:
    # Implementation that returns different types based on format
    pass

# repository/user_repo.pyi
from typing import overload, List, Dict, Any, Literal
import pandas as pd
from .models import User

# Multiple overloads to show different return types
@overload
def find_users(
    filters: Dict[str, Any] | None = None,
    *,
    limit: int = 100,
    offset: int = 0,
    format: Literal["json"] = "json"
) -> List[User]: ...

@overload
def find_users(
    filters: Dict[str, Any] | None = None,
    *,
    limit: int = 100,
    offset: int = 0,
    format: Literal["dataframe"]
) -> pd.DataFrame: ...
```

### 4. Functions with no runtime arguments

For functions that have no arguments after `/`, the stub should show an empty parameter list:

```python
# config/settings.py
from pinjected import injected

@injected
def get_config(
    env_vars: IProxy[dict],
    config_file: IProxy[Path],
    /
) -> Config:
    # Implementation
    pass

# config/settings.pyi
from typing import overload
from .models import Config

@overload
def get_config() -> Config: ...
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
   - Autocomplete shows only the arguments users need to provide
   - Parameter hints display runtime arguments correctly
   - Go-to-definition navigates to clean signatures

2. **Type Checking:**
   - mypy and other type checkers understand the user-facing interface
   - Catches type errors at development time
   - Documents expected types clearly

3. **API Documentation:**
   - Stub files serve as concise API documentation
   - Clear separation of runtime interface from implementation details
   - Easy to see all public functions at a glance

## Generating Stub Files

The linter provides suggested stub content when violations are found. You can also use tools:

```bash
# Manual creation based on linter suggestions
touch services/user_service.pyi
# Copy the suggested content from the linter output

# Note: Standard stubgen tools won't generate the correct @overload format
# Use the linter's suggestions for proper pinjected stub files
```

## Key Differences from Standard Stubs

1. **Use @overload instead of @injected**: All functions get `@overload` decorator
2. **Show only runtime arguments**: Omit everything before `/`
3. **No dependency imports**: Don't import injected dependency types
4. **Original return types**: Keep return types as-is (no IProxy transformation)

## Related Rules

- **PINJ011:** IProxy type annotations (ensures proper typing)
- **PINJ016:** Missing protocol parameter in @injected

## See Also

- [PEP 484 - Stub Files](https://www.python.org/dev/peps/pep-0484/#stub-files)
- [Pinjected Type Safety Guide](https://pinjected.readthedocs.io/type-safety)
- [How to Use Pinjected - .pyi Files Section](docs/how_to_use_pinjected.md#creating-pyi-stub-files)

## Version History

- **2.0.0:** Complete rewrite to use @overload for user-facing signatures
- **1.0.0:** Initial implementation with @injected decorators (deprecated)