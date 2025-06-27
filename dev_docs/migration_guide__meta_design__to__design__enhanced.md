# Enhanced Migration Guide: From `__meta_design__` to `__design__`

## Table of Contents
1. [Quick Start](#quick-start)
2. [Understanding the Change](#understanding-the-change)
3. [Migration Patterns](#migration-patterns)
4. [Common Scenarios](#common-scenarios)
5. [Testing Your Migration](#testing-your-migration)
6. [Troubleshooting](#troubleshooting)
7. [FAQ](#faq)
8. [Migration Checklist](#migration-checklist)

## Quick Start

**TL;DR**: Replace `__meta_design__` with `__design__` and move it to `__pinjected__.py` files.

```python
# Before: your_module/__init__.py
__meta_design__ = design(overrides=design(...))

# After: your_module/__pinjected__.py
__design__ = design(...)  # Note: no "overrides" wrapper needed
```

## Understanding the Change

### What's Deprecated
- `__meta_design__` variable in any Python file
- `design(overrides=design(...))` pattern
- Loading designs from `__init__.py` files

### What's New
- `__design__` variable in `__pinjected__.py` files
- Direct design specification without `overrides` wrapper
- Cleaner separation between code and configuration

### How Pinjected Resolves Designs

When running `python -m pinjected run your.module.function`, Pinjected:
1. Walks up the module hierarchy
2. Looks for `__pinjected__.py` files in each directory
3. Loads `__design__` variables from these files
4. Accumulates designs from parent to child
5. Falls back to `__meta_design__` for backward compatibility (with warnings)

## Migration Patterns

### Pattern 1: Simple Migration
**Scenario**: `__meta_design__` in `__init__.py`

```python
# Before: myapp/services/__init__.py
from pinjected import design
__meta_design__ = design(
    overrides=design(
        api_key="test-key",
        timeout=30
    )
)
```

```python
# After: myapp/services/__pinjected__.py
from pinjected import design
__design__ = design(
    api_key="test-key",
    timeout=30
)
```

### Pattern 2: With Injected Bindings
**Scenario**: Binding functions and classes

```python
# Before: myapp/db/__init__.py
from pinjected import design, Injected
from .connection import create_connection

__meta_design__ = design(
    overrides=design(
        db_connection=Injected.bind(create_connection),
        pool_size=10
    )
)
```

```python
# After: myapp/db/__pinjected__.py
from pinjected import design, Injected
from .connection import create_connection

__design__ = design(
    db_connection=Injected.bind(create_connection),
    pool_size=10
)
```

### Pattern 3: With Decorated Functions
**Scenario**: Using `@injected` and `@instance` decorators

```python
# Before: myapp/cache/__init__.py
from pinjected import design, injected, instance

@injected
def get_cache_client(redis_url: str, /) -> CacheClient:
    return RedisClient(redis_url)

@instance
def singleton_logger(config: dict, /) -> Logger:
    return Logger(config)

__meta_design__ = design(
    overrides=design(
        cache_client=get_cache_client,
        logger=singleton_logger,
        redis_url="localhost:6379"
    )
)
```

```python
# After: myapp/cache/__pinjected__.py
from pinjected import design, injected, instance
from .implementations import RedisClient, Logger

@injected
def get_cache_client(redis_url: str, /) -> CacheClient:
    return RedisClient(redis_url)

@instance
def singleton_logger(config: dict, /) -> Logger:
    return Logger(config)

__design__ = design(
    cache_client=get_cache_client,  # No Injected.bind() needed
    logger=singleton_logger,        # No Injected.bind() needed
    redis_url="localhost:6379"
)
```

### Pattern 4: Importing Other Designs
**Scenario**: Composing designs from multiple sources

```python
# Before: myapp/api/__init__.py
from pinjected import design
from myapp.common import common_design
from myapp.auth import auth_design

__meta_design__ = design(
    overrides=common_design + auth_design + design(
        api_version="v2",
        rate_limit=100
    )
)
```

```python
# After: myapp/api/__pinjected__.py
from pinjected import design
from myapp.common import common_design
from myapp.auth import auth_design

__design__ = common_design + auth_design + design(
    api_version="v2",
    rate_limit=100
)
```

### Pattern 5: Non-__init__.py Files
**Scenario**: `__meta_design__` in regular Python files

```python
# Before: myapp/services/email_service.py
from pinjected import design, Injected

def send_email(smtp_host: str, message: str):
    # Implementation
    pass

__meta_design__ = design(
    overrides=design(
        email_sender=Injected.bind(send_email),
        smtp_host="mail.example.com"
    )
)
```

```python
# After: myapp/services/email_service.py
from pinjected import design, Injected

def send_email(smtp_host: str, message: str):
    # Implementation
    pass

# Simply rename to __design__ and remove overrides wrapper
__design__ = design(
    email_sender=Injected.bind(send_email),
    smtp_host="mail.example.com"
)
```

## Common Scenarios

### Scenario 1: Nested Module Structure
```
myapp/
├── __pinjected__.py         # Root design
├── services/
│   ├── __pinjected__.py     # Services design (inherits root)
│   └── auth/
│       └── __pinjected__.py # Auth design (inherits services + root)
```

### Scenario 2: Mixed Old and New
During migration, you might have both patterns:

```python
# myapp/__init__.py (old style - will trigger warnings)
__meta_design__ = design(overrides=design(...))

# myapp/__pinjected__.py (new style - takes precedence)
__design__ = design(...)
```

### Scenario 3: Testing Modules
```python
# tests/__pinjected__.py
from pinjected import design
from myapp import production_design

# Override production settings for tests
__design__ = production_design + design(
    db_url="sqlite:///:memory:",
    api_key="test-key",
    debug=True
)
```

## Testing Your Migration

### 1. Check for Warnings
Run your application and look for deprecation warnings:
```
WARNING: Use of __meta_design__ in myapp.services is deprecated.
Please migrate to using __design__ in __pinjected__.py instead.
```

### 2. Verify Design Loading
```python
# test_migration.py
from pinjected.module_helper import walk_module_with_special_files

# Check that designs are being loaded correctly
for var in walk_module_with_special_files(
    Path("myapp"),
    attr_names=["__design__"],
    special_filenames=["__pinjected__.py"]
):
    print(f"Found design at: {var.var_path}")
```

### 3. Unit Tests
```python
import pytest
from pinjected import Design
from myapp import __design__ as app_design

def test_design_bindings():
    # Verify expected bindings exist
    assert "api_key" in app_design.bindings
    assert "db_connection" in app_design.bindings
```

## Troubleshooting

### Issue 1: Design Not Found
**Symptom**: `DependencyResolutionError: No binding for 'my_dependency'`

**Solution**: Ensure `__pinjected__.py` is in the correct directory and contains `__design__`.

### Issue 2: Circular Import
**Symptom**: `ImportError` when creating `__pinjected__.py`

**Solution**: Use lazy imports or import only what's needed:
```python
# __pinjected__.py
from pinjected import design, Injected

def _get_implementation():
    # Lazy import to avoid circular dependency
    from .implementation import MyClass
    return MyClass

__design__ = design(
    my_service=Injected.bind(_get_implementation)
)
```

### Issue 3: Overrides Not Working
**Symptom**: Design bindings aren't being applied as expected

**Solution**: Remember that child designs override parent designs:
```python
# parent/__pinjected__.py
__design__ = design(debug=False)

# parent/child/__pinjected__.py
__design__ = design(debug=True)  # This overrides parent
```

## FAQ

**Q: Can I have both `__meta_design__` and `__design__` during migration?**
A: Yes, but `__design__` takes precedence and you'll see deprecation warnings.

**Q: What happens to `default_design_paths`?**
A: This pattern is deprecated. Import designs directly instead.

**Q: Should I keep backward compatibility?**
A: Only if you have external code depending on `__meta_design__`. Otherwise, migrate fully.

**Q: Can I use `__design__` in regular Python files?**
A: Yes, but prefer `__pinjected__.py` for consistency and better tool support.

## Migration Checklist

- [ ] **Identify all `__meta_design__` occurrences**
  ```bash
  grep -r "__meta_design__" --include="*.py" .
  ```

- [ ] **For each `__meta_design__` in `__init__.py`:**
  - [ ] Create `__pinjected__.py` in the same directory
  - [ ] Copy the design configuration
  - [ ] Remove `overrides=` wrapper
  - [ ] Test that bindings still work

- [ ] **For each `__meta_design__` in other files:**
  - [ ] Rename to `__design__`
  - [ ] Remove `overrides=` wrapper
  - [ ] Consider moving to `__pinjected__.py`

- [ ] **Update imports:**
  - [ ] Change `from module import __meta_design__` to `from module import __design__`
  - [ ] Update any dynamic design loading code

- [ ] **Test thoroughly:**
  - [ ] Run all unit tests
  - [ ] Check for deprecation warnings
  - [ ] Verify all dependencies resolve correctly
  - [ ] Test in development environment

- [ ] **Clean up (Phase 2):**
  - [ ] Remove old `__meta_design__` variables
  - [ ] Update documentation
  - [ ] Inform team members

- [ ] **Monitor:**
  - [ ] Watch for any runtime errors
  - [ ] Check application logs for warnings
  - [ ] Ensure performance hasn't degraded

## Next Steps

1. Start with leaf modules (those without dependencies)
2. Work your way up to root modules
3. Test each migration before moving to the next
4. Consider automating with a migration script for large codebases

## Additional Resources

- [Original Migration Guide](./migration_guide__meta_design__to__design__original.md)
- [Manual Migration Steps](./migration_guide__meta_design__to__design__manual_steps.md)
- [Pinjected Documentation](https://github.com/CyberAgentAILab/pinjected)
- [Design Patterns Best Practices](../docs/best_practices.md)