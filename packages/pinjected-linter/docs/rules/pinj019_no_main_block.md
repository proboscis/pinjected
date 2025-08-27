# PINJ019: No Main Block

## Overview

**Rule ID:** PINJ019  
**Category:** Best Practices  
**Severity:** Error  
**Auto-fixable:** No

Files containing `@injected` or `@instance` decorated functions should not use `if __name__ == "__main__":` blocks.

## Rationale

Pinjected is designed to be run using the CLI command `python -m pinjected run <module.function>` rather than traditional Python script execution. Using `__main__` blocks goes against Pinjected's design philosophy and reduces the flexibility that comes with dependency injection.

Key reasons why `__main__` blocks should be avoided:

1. **Configuration flexibility**: CLI execution allows easy parameter overrides and dependency switching
2. **Testability**: Functions can be tested in isolation without executing main logic
3. **Reusability**: Entry points can be composed and reused in different contexts
4. **Consistency**: Maintains a uniform execution pattern across the codebase

## Rule Details

This rule flags files that contain both:
- Functions decorated with `@injected` or `@instance`
- An `if __name__ == "__main__":` block

### Examples of Violations

❌ **Bad:** Using main block with pinjected functions
```python
from pinjected import instance, injected

@instance
def database():
    return Database()

@injected
def process_data(database, /, data: str):
    return database.process(data)

# This violates PINJ019
if __name__ == "__main__":
    # Traditional execution - NOT recommended
    result = process_data("some data")
    print(result)
```

✅ **Good:** Using pinjected CLI execution
```python
from pinjected import instance, injected, IProxy

@instance
def database():
    return Database()

@injected
def process_data(database, /, data: str):
    return database.process(data)

# Define entry points as IProxy variables
run_process: IProxy = process_data("some data")
```

Then execute using:
```bash
python -m pinjected run mymodule.run_process
```

## Common Patterns and Best Practices

### 1. Define Entry Points as IProxy Variables

```python
from pinjected import injected, IProxy

@injected
def train_model(trainer, dataset, /, epochs: int):
    return trainer.train(dataset, epochs)

# Create entry points
run_training: IProxy = train_model(epochs=100)
run_quick_test: IProxy = train_model(epochs=1)
```

### 2. Use CLI for Parameter Overrides

```bash
# Override parameters at runtime
python -m pinjected run mymodule.run_training --epochs=50

# Switch dependencies
python -m pinjected run mymodule.run_training --dataset='{mymodule.test_dataset}'
```

### 3. For Scripts That Need Main Blocks

If you have a script that genuinely needs a main block (e.g., utility scripts), keep pinjected functions in separate modules:

```python
# utils.py - pinjected functions
from pinjected import instance

@instance
def logger():
    return Logger()

# script.py - traditional script without pinjected
from utils import some_utility  # Regular imports, not pinjected

if __name__ == "__main__":
    # OK - No pinjected functions in this file
    some_utility()
```

## Migration Guide

To migrate from main block execution to pinjected CLI:

1. **Remove the main block**:
```python
# Remove this:
if __name__ == "__main__":
    result = my_function()
    print(result)
```

2. **Create IProxy entry points**:
```python
# Add this:
run_my_function: IProxy = my_function()
```

3. **Execute via CLI**:
```bash
python -m pinjected run mymodule.run_my_function
```

## Configuration

This rule has no configuration options.

## When to Disable

You might want to disable this rule if:
- You're migrating legacy code gradually
- You have utility scripts that mix pinjected and non-pinjected code
- You're creating examples or documentation that show both patterns

To disable for a specific file:
```python
# noqa: PINJ019
```

To disable in configuration:
```toml
[tool.pinjected-linter]
disable = ["PINJ019"]
```

## Related Rules

- **PINJ001:** Instance naming convention
- **PINJ005:** Injected function naming convention

## Further Reading

- [Pinjected Execution Guide](https://pinjected.readthedocs.io/en/latest/)
- [Entry Point Design Best Practices](https://pinjected.readthedocs.io/en/latest/#entry-point-design-best-practices)

## Version History

- **1.0.0:** Initial implementation