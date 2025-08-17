# PINJ061: Enforce module-level __design__ in pytest files

Pytest modules must define a top-level `__design__` variable to enable dependency resolution when using `@injected_pytest`.

- Applies to: Python files whose name starts with `test_` and ends with `.py`
- Why: `@injected_pytest` relies on a module-level `__design__` to resolve injected dependencies into pytest function arguments. Dependencies referenced in test parameters must be bound in `__design__`.
- Reference: See the usage guide for patterns and best practices in docs/how_to_use_pinjected.md

- See also: PINJ040 (use @injected_pytest), PINJ043 (no design() inside test functions)

## Bad

Missing `__design__`:

```py
# test_example.py
from pinjected.test import injected_pytest

@injected_pytest
def test_example(logger):
    assert logger is not None
```

This will raise PINJ061.

## Good

Define `__design__` at module level, bind dependencies there, and use `@injected_pytest`:

```py
# test_example.py
from pinjected import design, instance
from pinjected.test import injected_pytest

__design__ = design(
    logger=instance("test-logger")
)

@injected_pytest
def test_example(logger):
    assert logger == "test-logger"
```

## Message

Pytest module is missing a module-level `__design__` variable. Define and bind dependencies:

```py
from pinjected import design, instance
from pinjected.test import injected_pytest

__design__ = design(
    x=instance(42)
)

@injected_pytest
def test_example(x):
    assert x == 42
```

This ensures `@injected_pytest` can resolve dependencies for your test functions.
