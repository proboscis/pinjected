# PINJ064: No Optional Dependencies in @injected/@instance

## Overview
Forbid using Optional[T] or Union[T, None] for dependency parameters in @injected and @instance functions. Dependencies are parameters before the "/" separator. If no "/" is present, all parameters are treated as dependencies.

## Rationale
In pinjected, dependency optionality should be modeled via the DI system, not with Optional types. Use alternate providers or design overrides to supply different implementations or absence handling. Returning None from dependencies or annotating dependencies as Optional[T] creates ambiguity and hides configuration responsibilities that should live in the design.

## Examples

### ❌ Bad
```
from typing import Optional, Union
from pinjected import injected, instance

@injected
def build_service(client: Optional["ApiClient"], /):
    ...

@instance
def provide_logger(logger: Union["Logger", None], /):
    ...
```

### ✅ Good
```
from pinjected import injected, instance

@injected
def build_service(client, /):
    ...

# In __pinjected__.py or a design composition:
# __design__ = design(client=real_client)
# test design can override:
# test_design = __design__ + design(client=fake_client)

@instance
def provide_logger(logger, /):
    ...
```

## Notes
- Only parameters before "/" are considered dependencies. Parameters after "/" (regular arguments) are not checked by this rule.
- For async @injected functions, follow existing naming rules (a_-prefix), and apply this rule to dependency annotations the same way.
