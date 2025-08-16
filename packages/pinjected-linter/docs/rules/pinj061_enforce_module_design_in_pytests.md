# PINJ061: Enforce module-level __design__ in pytest files

Pytest modules must define a top-level `__design__` variable to enable dependency resolution when using `@injected_pytest`.

- Applies to: Python files whose name starts with `test_` and ends with `.py`
- Why: `@injected_pytest` relies on a module-level `__design__` to resolve injected dependencies into pytest function arguments
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

Define `__design__` at module level and use `@injected_pytest`:

```py
# test_example.py
from pinjected import design
from pinjected.test import injected_pytest

__design__ = design()

@injected_pytest
def test_example(logger):
    assert logger is not None
```

## Message

Pytest module is missing a module-level `__design__` variable. Define:

```py
from pinjected import design
from pinjected.test import injected_pytest

__design__ = design()

@injected_pytest
def test_example(dep):
    ...
```

This ensures `@injected_pytest` can resolve dependencies for your test functions.
