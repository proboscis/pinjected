# PINJ036: Enforce .pyi stub files

## Summary

All Python modules should have corresponding `.pyi` stub files with complete public API signatures for better IDE support and type checking.

## Details

This rule enforces that every Python module has a corresponding `.pyi` stub file that contains type annotations for all public API elements. This helps with:

- Better IDE support (autocompletion, type hints)
- Static type checking with tools like mypy
- Clear API documentation
- Preventing breaking changes in public APIs

The rule checks for:
1. Existence of `.pyi` files for all Python modules
2. Completeness of public API declarations in stub files
3. Proper type annotations for all public functions, classes, and variables

### Exclusions

The following files are automatically excluded from this check:
- Files starting with `test` (e.g., `test_module.py`)
- Files in `tests/` or `test/` directories
- Files in `migrations/` directories
- Temporary files

### What constitutes public API?

Public API elements are those that don't start with an underscore (`_`), including:
- Module-level functions
- Module-level classes
- Module-level variables
- Class methods (except private ones starting with `_`)

The exception is `__init__` which is considered public despite having underscores.

## Examples

### ❌ Incorrect

**`mymodule.py`** without a corresponding `.pyi` file:
```python
def public_function(x: int) -> str:
    return str(x)

class MyClass:
    def method(self) -> None:
        pass

PUBLIC_CONSTANT = 42
```

**`mymodule.py`** with incomplete `.pyi` file:
```python
# mymodule.py
def function_one(x: int) -> str:
    return str(x)

def function_two(y: str) -> int:
    return len(y)

class MyClass:
    def method(self) -> None:
        pass
```

```python
# mymodule.pyi (incomplete - missing function_two and MyClass)
def function_one(x: int) -> str: ...
```

### ✅ Correct

**`mymodule.py`** with complete `.pyi` file:
```python
# mymodule.py
def public_function(x: int) -> str:
    return str(x)

async def async_function(data: dict) -> None:
    await process(data)

class MyClass:
    def __init__(self, name: str):
        self.name = name
    
    def method(self) -> None:
        pass
    
    def _private_method(self) -> None:
        # This doesn't need to be in the stub
        pass

PUBLIC_CONSTANT: int = 42

_private_var = "hidden"  # This doesn't need to be in the stub
```

```python
# mymodule.pyi (complete)
from typing import Any

PUBLIC_CONSTANT: int

def public_function(x: int) -> str: ...

async def async_function(data: dict) -> None: ...

class MyClass:
    def __init__(self, name: str) -> None: ...
    def method(self) -> None: ...
```

### Test files are excluded

Files starting with `test` are automatically excluded:
```python
# test_mymodule.py - No stub file required
def test_something():
    assert True
```

## Rationale

Type stub files (`.pyi`) provide several benefits:

1. **Type Safety**: They enable static type checkers to verify type correctness
2. **IDE Support**: Modern IDEs use stub files for better code completion and inline documentation
3. **API Documentation**: Stub files serve as a concise API reference
4. **Backward Compatibility**: Changes to stub files can highlight breaking API changes

## Configuration

This rule can be configured in your `pyproject.toml`:

```toml
[tool.pinjected-linter]
# Disable the rule entirely
disable = ["PINJ036"]

# Or configure specific options (when available)
[tool.pinjected-linter.rules.PINJ036]
# Future configuration options may include:
# - check_completeness = true  # Whether to check if stub files are complete
# - exclude_patterns = ["**/generated/**"]  # Additional exclusion patterns
```

## See Also

- [PEP 484 - Type Hints](https://www.python.org/dev/peps/pep-0484/)
- [PEP 561 - Distributing and Packaging Type Information](https://www.python.org/dev/peps/pep-0561/)
- [mypy documentation on stub files](https://mypy.readthedocs.io/en/stable/stubs.html)