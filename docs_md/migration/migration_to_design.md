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
    z=[1, 2, 3],
    add_one=lambda x:x+1
)

# After migration
design += design(
    x=0,
    y="string",
    z=[1, 2, 3],
    add_one=lambda x:x+1
)
```

### 2. `providers()` → `design()` + `Injected.bind()`

`providers()` binds functions or lambdas, which need to be wrapped with `Injected.bind()`.

```python
# Before migration
def create_something(x):
    return x+1
@injected
def injected_func(dep1):
    return dep1+'x'
@injected
async def a_injected_func(dep1):
    return dep1+'a'
@instance
def singleton_object1(dep1):
    return dep1 + 'this is singleton'
@instance
async def singleton_object2_async(dep1):
    return dep1 + "this is singleton with async"

design += providers(
    calc=lambda x, y: x + y,
    factory=create_something,
    func1 = injected_func,
    a_func1 = a_injected_func,
    singleton1 = singleton_object1,
    singleton2 = singleton_object2_async,
)

# After migration
design += design(
    calc=Injected.bind(lambda x, y: x + y),
    factory=Injected.bind(create_something),
    func1 = injected_func,
    a_func1 = a_injected_func,
    singleton1 = singleton_object1,
    singleton2 = singleton_object2_async,
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

### 1. Using `Injected.pure()` for providing a function.

```python
# For simple functions without dependencies
# before, providing a function with instances
design = instances(
    add_one = lambda x:x + 1
)
# After, providing a function requires wrapping with Injected.pure
design += design(
    #add_one = lambda x: x+1, # this is valid but Injected.pure is more explicit.
    add_one=Injected.pure(lambda x: x + 1),
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

## Summary

Basic principles for migration:

1. Pass simple values directly as `design(key=value)`
2. Always run tests to verify functionality

Following this migration guide will enable a smooth transition from the deprecated APIs to the new unified API.
