# Migration Guide: From instances(), providers(), classes() to design()

This guide explains the steps and patterns for migrating from the deprecated `instances()`, `providers()`, and `classes()` functions to the new unified `design()` API.

## Why Migration is Necessary

Pinjected has improved its API design to handle dependency injection in a more consistent way. Replacing multiple specialized functions with a single unified `design()` function offers the following benefits:

- Simpler and more consistent API
- Improved type hints and IDE completion
- More explicit declaration of dependencies
- Better compatibility and maintainability

## Basic Migration Patterns

### 1. `instances()` → `design()`

`instances()` binds simple values, so it can be directly replaced with `design()`.

```python
# Before migration
design += instances(
    x=0,
    y="string",
    z=[1, 2, 3]
)

# After migration
design += design(
    x=0,
    y="string",
    z=[1, 2, 3]
)
```

### 2. `providers()` → `design()` + `Injected.bind()`

`providers()` binds functions or lambdas, which need to be wrapped with `Injected.bind()`.

```python
# Before migration
design += providers(
    calc=lambda x, y: x + y,
    factory=create_something
)

# After migration
design += design(
    calc=Injected.bind(lambda x, y: x + y),
    factory=Injected.bind(create_something)
)
```

### 3. `classes()` → `design()` + `Injected.bind()`

`classes()` binds classes, which similarly need to be wrapped with `Injected.bind()`.

```python
# Before migration
design += classes(
    MyClass=MyClass,
    OtherClass=OtherClass
)

# After migration
design += design(
    MyClass=Injected.bind(MyClass),
    OtherClass=Injected.bind(OtherClass)
)
```

## Composite Patterns: Combining Multiple Functions

When using multiple deprecated functions, they can be combined into a single `design()` call:

```python
# Before migration
design = instances(
    x=0,
    y="string"
) + providers(
    factory=create_something
) + classes(
    MyClass=MyClass
)

# After migration
design = design(
    x=0,
    y="string",
    factory=Injected.bind(create_something),
    MyClass=Injected.bind(MyClass)
)
```

## Special Cases

### 1. Using `Injected.pure()`

For simple functions without dependencies, using `Injected.pure()` instead of `Injected.bind()` can improve performance:

```python
# For simple functions without dependencies
design += design(
    add_one=Injected.pure(lambda x: x + 1),
    constant_provider=Injected.pure(lambda: "constant value")
)
```

### 2. Handling Async Functions

The correct way to handle async functions:

```python
# Before migration
design += providers(
    async_factory=async_create_something
)

# After migration
design += design(
    async_factory=Injected.bind(lambda: async_create_something())
)
```

### 3. Resolving Variable Name Conflicts

When the variable name `design` conflicts with the imported `design()` function:

```python
# Before migration
design = instances(...)
design += providers(...)

# After migration - Method 1: Use an alias when importing
from pinjected import design as design_fn
design = design_fn(...)
design += design_fn(...)

# After migration - Method 2: Change the variable name
design_obj = design(...)
design_obj += design(...)
```

## Important Notes

1. Converting `instances()` → `design()` requires no additional modifications
2. Converting `providers()` and `classes()` → `design()` always requires wrapping with `Injected.bind()`
3. Be especially careful when performing search-and-replace across the entire workspace in an IDE (use pattern matching to correctly identify)
4. Don't just rely on simple replacements; run tests after migration to verify functionality
5. Always wrap class constructors with `Injected.bind()` when passing them directly
6. Be careful of key duplication in composite conversions

## Troubleshooting After Migration

### 1. Injection Resolution Errors

If you encounter `TypeError` or `KeyError`:

- Check for the presence of `Injected.bind()` wrappers
- Ensure classes and functions are not passed directly
- Check for duplicate dependency keys

### 2. Variable Name Conflicts

For errors due to name conflicts between the `design` variable and the `design()` function:

- Use an alias when importing: `from pinjected import design as design_fn`
- Change the variable name to something else: e.g., `design_obj`

### 3. Async Function Issues

Problems when binding async functions directly:

- Use the `Injected.bind(lambda: async_func())` pattern for async functions
- Verify correct usage of `async`/`await` patterns

## Summary

Basic principles for migration:

1. Pass simple values directly as `design(key=value)`
2. Wrap functions and classes as `design(key=Injected.bind(func))`
3. Consider `Injected.pure()` for simple functions without dependencies
4. Always run tests to verify functionality

Following this migration guide will enable a smooth transition from the deprecated APIs to the new unified API.