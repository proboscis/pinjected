# Migration from __meta_design__ to __design__ - Summary

This directory contains comprehensive resources for migrating from the deprecated `__meta_design__` pattern to the new `__design__` pattern in Pinjected.

## Available Resources

### 1. Original Migration Guide
**File**: `migration_guide__meta_design__to__design__original.md`
- Basic migration instructions
- Simple examples
- Original documentation from the Pinjected team

### 2. Enhanced Migration Guide
**File**: `migration_guide__meta_design__to__design__enhanced.md`
- Comprehensive guide with detailed examples
- Common scenarios and edge cases
- Troubleshooting section
- FAQ section
- Complete migration checklist
- Testing strategies

### 3. Manual Migration Steps
**File**: `migration_guide__meta_design__to__design__manual_steps.md`
- Step-by-step manual migration instructions
- Shell commands to find and verify changes
- Common patterns and how to fix them
- Quick reference card
- Troubleshooting tips

## Quick Migration Process

### 1. Find all __meta_design__ usage
```bash
grep -r "__meta_design__" --include="*.py" . | grep -v "__pycache__"
```

### 2. For each __init__.py with __meta_design__
- Create a `__pinjected__.py` file in the same directory
- Copy the design configuration
- Remove the `overrides=` wrapper

### 3. For other Python files
- Rename `__meta_design__` to `__design__`
- Remove the `overrides=` wrapper if present

### 4. Verify your migration
```bash
# Check no __meta_design__ remains
grep -r "__meta_design__" --include="*.py" . | grep -v "__pycache__" | grep -v "^[[:space:]]*#"

# Verify __pinjected__.py files exist
find . -name "__pinjected__.py" -type f
```

## Key Changes at a Glance

| Before | After |
|--------|-------|
| `__meta_design__` in any file | `__design__` in `__pinjected__.py` |
| `design(overrides=design(...))` | `design(...)` |
| In `__init__.py` files | In `__pinjected__.py` files |
| Deprecation warnings | Clean, modern approach |

## Example Migration

**Before** (`services/__init__.py`):
```python
from pinjected import design
__meta_design__ = design(
    overrides=design(
        api_key="test",
        timeout=30
    )
)
```

**After** (`services/__pinjected__.py`):
```python
from pinjected import design
__design__ = design(
    api_key="test",
    timeout=30
)
```

## Need Help?

1. Check `migration_guide__meta_design__to__design__manual_steps.md` for detailed shell commands
2. Read `migration_guide__meta_design__to__design__enhanced.md` for comprehensive examples
3. Refer to the troubleshooting sections in both guides

## Timeline

- **Current**: Both patterns work, but `__meta_design__` shows deprecation warnings
- **Future**: `__meta_design__` support will be removed
- **Recommendation**: Migrate as soon as possible to avoid future issues

## Safety Tips

- Always backup your code before migration
- Test thoroughly after each file migration
- Consider migrating one module at a time
- Keep the old `__meta_design__` code commented out until you verify everything works