# PINJ046: Mutable Attribute Naming

## Summary

Class attributes that are assigned outside of `__init__` or `__post_init__` are considered mutable and must follow specific naming conventions:
- Public mutable attributes must be prefixed with `mut_`
- Private mutable attributes must be prefixed with `_mut`

## Rationale

In object-oriented programming, attributes that are modified after initialization are considered mutable state. These mutable attributes can make code harder to reason about and debug, as the object's state can change at any time.

By enforcing a naming convention for mutable attributes, we:
1. Make the mutable nature of attributes explicit
2. Help developers quickly identify which parts of an object can change
3. Encourage thoughtful consideration about whether an attribute needs to be mutable
4. Improve code readability and maintainability

## Examples

### ❌ Incorrect

```python
class Counter:
    def __init__(self):
        self.value = 0  # Looks immutable but is actually mutable
        self._internal_state = "ready"
    
    def increment(self):
        self.value += 1  # PINJ046: 'value' should be 'mut_value'
    
    def update_state(self, new_state):
        self._internal_state = new_state  # PINJ046: '_internal_state' should be '_mut_internal_state'
```

```python
class DataProcessor:
    def __init__(self):
        self.processed_count = 0
        self.errors = []
    
    def process(self, data):
        try:
            # Process data
            self.processed_count += 1  # PINJ046: Should be mut_processed_count
        except Exception as e:
            self.errors.append(str(e))  # PINJ046: Should be mut_errors
```

### ✅ Correct

```python
class Counter:
    def __init__(self):
        self.mut_value = 0  # Clearly marked as mutable
        self._mut_internal_state = "ready"
    
    def increment(self):
        self.mut_value += 1  # OK: Properly named mutable attribute
    
    def update_state(self, new_state):
        self._mut_internal_state = new_state  # OK: Properly named private mutable attribute
```

```python
class DataProcessor:
    def __init__(self):
        self.mut_processed_count = 0
        self.mut_errors = []
    
    def process(self, data):
        try:
            # Process data
            self.mut_processed_count += 1  # OK
        except Exception as e:
            self.mut_errors.append(str(e))  # OK
```

```python
class ImmutableConfig:
    def __init__(self, config_dict):
        # These are only set in __init__, so they don't need mut_ prefix
        self.host = config_dict['host']
        self.port = config_dict['port']
        self.timeout = config_dict['timeout']
    
    def get_url(self):
        # Only reading, not modifying
        return f"{self.host}:{self.port}"
```

## Special Cases

### `__post_init__` Method

Attributes assigned in `__post_init__` are treated the same as those in `__init__`:

```python
from dataclasses import dataclass

@dataclass
class Point:
    x: float
    y: float
    
    def __post_init__(self):
        self.magnitude = (self.x**2 + self.y**2)**0.5  # OK: Set during initialization
        self.mut_visits = 0  # Prepare for future mutations
    
    def visit(self):
        self.mut_visits += 1  # OK: Properly named mutable attribute
```

### Dunder Attributes

Double-underscore (dunder) attributes are ignored by this rule as they follow Python's name mangling convention:

```python
class Private:
    def __init__(self):
        self.__secret = "hidden"
    
    def update(self):
        self.__secret = "updated"  # OK: Dunder attributes are special
```

## Suppression

If you need to suppress this rule for a specific line, use the `# noqa: PINJ046` comment:

```python
class LegacyClass:
    def __init__(self):
        self.counter = 0
    
    def increment(self):
        self.counter += 1  # noqa: PINJ046
```

However, it's strongly recommended to refactor your code to follow the naming convention rather than suppressing the rule.

## Configuration

This rule has no configuration options. The naming convention is fixed:
- Public mutable attributes: `mut_` prefix
- Private mutable attributes: `_mut` prefix

## See Also

- PINJ047: Maximum Mutable Attributes - Limits the number of mutable attributes per class
- Python's property decorators for creating controlled access to attributes
- The concept of immutability in functional programming