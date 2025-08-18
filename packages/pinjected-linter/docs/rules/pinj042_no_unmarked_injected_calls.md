# PINJ042: No Unmarked Calls to @injected Functions

@injected functions are meant to be used through the dependency injection system. Calling them directly returns an IProxy rather than executing the function. This rule flags direct calls from non-@injected contexts unless they are explicitly marked as intentional.

## Why this matters

- Direct calls to @injected functions return IProxy objects rather than executing logic
- Encourages correct dependency wiring and type safety
- Prevents subtle runtime errors caused by bypassing dependency resolution

## Module-level calls

At module level, calling an @injected function defines an IProxy entrypoint. You must explicitly annotate the variable as IProxy[T] with an appropriate type parameter.

Correct usage:
```python
# Explicitly typed as IProxy with type parameter
my_entrypoint: IProxy[ServiceType] = make_service("arg")

# Avoid using Any; prefer a concrete type or a Protocol type parameter
# IProxy[Any] remains allowed but is discouraged
# my_entrypoint: IProxy[Any] = make_service("arg")
```

## Inside regular code

Do not call @injected functions directly inside regular functions, classes, or lambdas. Instead, declare the dependency in an @injected function or resolve via a design.

Example (dependency injection):
```python
from pinjected import injected

@injected
def use_service(service, /, data):
    return service(data)
```

Example (using Design):
```python
from pinjected import design

with design(service=make_service()) as d:
    result = d.run(lambda service: service("data"))
```

## In pytest tests

Do not call @injected functions directly in test functions. Instead, expose dependencies via fixtures derived from your design.

Outline:
1. Build a design at module level
2. Register fixtures using register_fixtures_from_design
3. Request the dependency as a fixture parameter in tests

```python
from pinjected import design
from pinjected.test import register_fixtures_from_design
from pinjected import injected

@injected
def make_service(dep, /): ...

test_design = design(
    service=make_service(),
)

register_fixtures_from_design(test_design)

def test_example(service):
    # service is the resolved dependency, not an IProxy
    assert service("x")
```

## Explicitly marking calls

You can suppress this rule where absolutely necessary by marking calls explicitly:
- Add a trailing comment: `# pinjected: explicit-call`
- Or use: `# noqa: PINJ042`

Use suppressions sparingly and only with reviewer approval, as they bypass normal DI safety checks.
