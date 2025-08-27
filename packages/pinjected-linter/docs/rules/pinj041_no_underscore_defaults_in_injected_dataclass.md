# PINJ041: No Default Values or Optional Types for Underscore-Prefixed Attributes in @injected @dataclass

## Overview

**Rule ID:** PINJ041  
**Category:** Design  
**Severity:** Error  
**Auto-fixable:** No

Attributes starting with `_` in classes decorated with both `@injected` and `@dataclass` should not have default values or be typed as `Optional`. These attributes are meant to be injected via pinjected, so default values have no effect and Optional types are inappropriate.

## Rationale

In pinjected, when using `@injected` with `@dataclass`, attributes prefixed with underscore (`_`) are treated as injected dependencies. Since these are injected by the framework:

1. Default values will be ignored and overwritten by injection
2. Optional types suggest the dependency might not be provided, which contradicts the injection pattern
3. This can lead to confusion about whether a dependency is required or optional
4. It may hide missing dependency configuration errors

## Rule Details

This rule flags any underscore-prefixed attribute in an `@injected @dataclass` that:
- Has a default value assigned
- Is typed as `Optional[T]`, `T | None`, or `Union[T, None]`

### Examples of Violations

❌ **Bad:** Underscore-prefixed attributes with defaults or Optional types
```python
from dataclasses import dataclass
from typing import Optional
from pinjected import injected

@injected
@dataclass
class ServiceA:
    _logger: Logger = get_default_logger()  # Default value
    _cache: Cache = None  # Default value
    name: str  # OK - not underscore-prefixed

@injected
@dataclass
class ServiceB:
    _database: Optional[Database]  # Optional type
    _auth_service: AuthService | None  # Union with None
    _config: Union[Config, None]  # Union with None

@injected
@dataclass
class ServiceC:
    _api_client: Optional[APIClient] = None  # Both Optional and default
```

✅ **Good:** Underscore-prefixed attributes without defaults or Optional types
```python
from dataclasses import dataclass
from pinjected import injected

@injected
@dataclass
class ServiceA:
    _logger: Logger  # Will be injected
    _cache: Cache  # Will be injected
    name: str = "default"  # OK - not underscore-prefixed

@injected
@dataclass
class ServiceB:
    _database: Database  # Required dependency
    _auth_service: AuthService  # Required dependency
    _config: Config  # Required dependency

# If you need optional behavior, use a different pattern
@injected
@dataclass
class ServiceC:
    _api_client: APIClient  # Always injected
    # Use a method to handle optional logic
    def get_optional_feature(self):
        if hasattr(self._api_client, 'optional_feature'):
            return self._api_client.optional_feature
        return None
```

## Common Patterns and Best Practices

### 1. Always inject required dependencies
```python
# ❌ Bad - suggesting optional dependency
@injected
@dataclass
class UserService:
    _db: Optional[Database]
    _cache: Optional[Cache] = None

# ✅ Good - clear required dependencies
@injected
@dataclass
class UserService:
    _db: Database
    _cache: Cache
```

### 2. Use design() for configuration, not defaults
```python
# ❌ Bad - using defaults
@injected
@dataclass
class EmailService:
    _smtp_client: SMTPClient = default_smtp_client()
    _template_engine: TemplateEngine = Jinja2Engine()

# ✅ Good - inject configured instances
@injected
@dataclass
class EmailService:
    _smtp_client: SMTPClient
    _template_engine: TemplateEngine

# Configure via design
email_design = design(
    _smtp_client=smtp_client,
    _template_engine=jinja2_engine
)
```

### 3. Handle optional features differently
```python
# ❌ Bad - optional dependency
@injected
@dataclass
class PaymentProcessor:
    _fraud_detector: Optional[FraudDetector]

# ✅ Good - always inject, handle optionality in implementation
@injected
@dataclass
class PaymentProcessor:
    _fraud_detector: FraudDetector  # Could be a NoOpFraudDetector

# Or use feature flags
@injected
@dataclass
class PaymentProcessor:
    _fraud_detector: FraudDetector
    _feature_flags: FeatureFlags
    
    def process_payment(self, amount):
        if self._feature_flags.is_enabled('fraud_detection'):
            self._fraud_detector.check(amount)
```

## Configuration

This rule has no configuration options.

## When to Disable

You should generally not disable this rule as it prevents common misunderstandings about dependency injection. However, you might disable it if:

- You're migrating from a different dependency injection system
- You have a custom injection mechanism that works with defaults

To disable for a specific class:
```python
# noqa: PINJ041
@injected
@dataclass
class LegacyService:
    _logger: Logger = get_default_logger()  # Legacy pattern
```

To disable in configuration:
```toml
[tool.pinjected-linter]
disable = ["PINJ041"]
```

## Related Rules

- **PINJ002:** Instance function default arguments (similar principle for @instance functions)
- **PINJ018:** Double @injected decorator detection

## See Also

- [Pinjected documentation on @injected decorator](https://pinjected.readthedocs.io/injected)
- [Pinjected documentation on dependency injection patterns](https://pinjected.readthedocs.io/patterns)

## Version History

- **1.0.0:** Initial implementation