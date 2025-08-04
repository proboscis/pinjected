# PINJ029: No Function/Class Calls Inside Injected.pure()

## Description

Detects when `Injected.pure()` is used with function calls or class instantiations, which causes code execution during module loading time. These should be replaced with the `IProxy` pattern for lazy evaluation.

## Why This Rule Exists

When you use `Injected.pure(SomeClass())` or `Injected.pure(some_function())`, the code inside the parentheses executes immediately when the module is loaded. This defeats the purpose of dependency injection, which should defer object creation until injection time.

Problems with immediate execution:
- Side effects occur during module import
- Dependencies are created before the injection framework is ready
- Configuration values may not be available yet
- Testing becomes harder as objects are created globally

## Examples

### ❌ Bad - Immediate Execution

```python
from pinjected import Injected

# These execute immediately during module loading
service = Injected.pure(MyService())  # Class instantiation
config = Injected.pure(get_config())   # Function call
db = Injected.pure(DatabaseClient(host="localhost", port=5432))  # With arguments
result = Injected.pure(obj.method())   # Method call
```

### ✅ Good - Lazy Evaluation with IProxy

```python
from pinjected import Injected, IProxy

# These defer execution until injection time
service = IProxy(MyService)()
config = IProxy(get_config)()
db = IProxy(DatabaseClient)(host="localhost", port=5432)
result = IProxy(obj.method)()
```

### ✅ Good - References Without Calls

```python
from pinjected import Injected

# These are fine - no immediate execution
factory = Injected.pure(MyFactory)        # Class reference
func = Injected.pure(get_config)          # Function reference
value = Injected.pure(42)                 # Literal value
lambda_ref = Injected.pure(lambda x: x)  # Lambda reference (not called)
```

## Common Patterns

### Configuration Loading

```python
# ❌ Bad - loads config during import
config = Injected.pure(load_config_from_file())

# ✅ Good - loads config when needed
config = IProxy(load_config_from_file)()
```

### Service Initialization

```python
# ❌ Bad - creates service during import
service = Injected.pure(EmailService(smtp_host="mail.example.com"))

# ✅ Good - creates service during injection
service = IProxy(EmailService)(smtp_host="mail.example.com")
```

## When to Disable This Rule

If you have a specific case where immediate execution is intentional and safe (e.g., creating immutable configuration objects with no side effects), you can disable this rule:

```python
# Safe because datetime.now() has no side effects and we want the import time
import_time = Injected.pure(datetime.now())  # noqa: PINJ029
```

## Configuration

This rule is enabled by default. To disable it globally, add to your `pyproject.toml`:

```toml
[tool.pinjected-linter]
disable = ["PINJ029"]
```

## See Also

- [IProxy documentation](https://github.com/CyberAgentAILab/pinjected#iproxy)
- [Dependency Injection Best Practices](https://github.com/CyberAgentAILab/pinjected#best-practices)