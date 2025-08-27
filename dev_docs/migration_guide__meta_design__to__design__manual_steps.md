# Manual Migration Steps: __meta_design__ to __design__

## Step 1: Find All __meta_design__ Usage

```bash
# Find all files with __meta_design__
grep -r "__meta_design__" --include="*.py" . | grep -v "__pycache__"

# Count occurrences
grep -r "__meta_design__" --include="*.py" . | grep -v "__pycache__" | wc -l

# Find __meta_design__ in __init__.py files specifically
find . -name "__init__.py" -type f -exec grep -l "__meta_design__" {} \;
```

## Step 2: Understand the Migration Pattern

### For __init__.py files:
1. Create a new `__pinjected__.py` file in the same directory
2. Copy the imports and __meta_design__ definition
3. Transform according to the pattern below

### For other .py files:
1. Simply rename `__meta_design__` to `__design__` in the same file
2. Remove the `overrides=` wrapper if present

## Step 3: Manual Migration Examples

### Example 1: Simple __init__.py Migration

**Before** (`myapp/services/__init__.py`):
```python
from pinjected import design

__meta_design__ = design(
    overrides=design(
        api_key="test-key",
        timeout=30
    )
)
```

**After** (create `myapp/services/__pinjected__.py`):
```python
from pinjected import design

__design__ = design(
    api_key="test-key",
    timeout=30
)
```

### Example 2: Regular File Migration

**Before** (`myapp/config.py`):
```python
from pinjected import design, Injected

__meta_design__ = design(
    overrides=design(
        db_url=Injected.bind(get_db_url)
    )
)
```

**After** (same file `myapp/config.py`):
```python
from pinjected import design, Injected

__design__ = design(
    db_url=Injected.bind(get_db_url)
)
```

## Step 4: Verify Your Changes

```bash
# Check that no __meta_design__ remains (except in comments/docs)
grep -r "__meta_design__" --include="*.py" . | grep -v "__pycache__" | grep -v "^[[:space:]]*#"

# Verify __pinjected__.py files were created
find . -name "__pinjected__.py" -type f

# Check for __design__ in your new files
grep -r "__design__" --include="__pinjected__.py" .
```

## Step 5: Test Your Migration

1. Run your test suite
2. Check for deprecation warnings in the output
3. Verify all dependencies resolve correctly

```bash
# Example test command (adjust for your project)
python -m pytest -v

# Or if using pinjected directly
python -m pinjected run your.module.function
```

## Common Patterns to Fix

### Pattern 1: Nested overrides
```python
# Before
__meta_design__ = design(
    overrides=design(
        overrides=design(...)  # Don't do this!
    )
)

# After
__design__ = design(...)  # Flatten it
```

### Pattern 2: With imports
```python
# Before (__init__.py)
from .config import config_design
__meta_design__ = design(
    overrides=config_design + design(...)
)

# After (__pinjected__.py)
from .config import config_design
__design__ = config_design + design(...)
```

### Pattern 3: Conditional designs
```python
# Before
import os
__meta_design__ = design(
    overrides=design(
        debug=os.getenv("DEBUG", "false") == "true"
    )
)

# After
import os
__design__ = design(
    debug=os.getenv("DEBUG", "false") == "true"
)
```

## Troubleshooting

### Issue: "No binding for X" after migration
- Check that `__pinjected__.py` is in the correct directory
- Ensure the file has `__design__` (not `__meta_design__`)
- Verify imports are correct

### Issue: Deprecation warnings still showing
- Search for any remaining `__meta_design__` usage
- Check imported modules that might still use old pattern

### Issue: Design not being loaded
- Pinjected looks for `__pinjected__.py` files, not `__init__.py`
- Make sure file permissions are correct
- Check for syntax errors in the new file

## Quick Reference Card

| Task | Command/Action |
|------|---------------|
| Find all __meta_design__ | `grep -r "__meta_design__" --include="*.py" .` |
| Create __pinjected__.py | `touch myapp/services/__pinjected__.py` |
| Test migration | `python -m pinjected run your.module.function` |
| Check for warnings | Look for "deprecated" in output |

## Migration Checklist

- [ ] Run grep to find all __meta_design__ occurrences
- [ ] For each __init__.py with __meta_design__:
  - [ ] Create __pinjected__.py in same directory
  - [ ] Copy and transform the design
  - [ ] Remove overrides= wrapper
- [ ] For each other .py file with __meta_design__:
  - [ ] Rename to __design__
  - [ ] Remove overrides= wrapper
- [ ] Run tests to verify
- [ ] Check for deprecation warnings
- [ ] Clean up old __meta_design__ code (optional, for later)