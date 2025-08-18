# PINJ062: No duplicate @injected/@instance function names

- Applies to: Functions decorated with `@injected` or `@instance`
- Why: Pinjected uses function names as global DI keys on import. If multiple providers share the same name, later imports override earlier ones, causing unexpected behavior and hard-to-debug overrides.

This rule raises an error when the same function name is used by multiple `@injected`/`@instance` functions anywhere in the codebase.

See also:
- PINJ006 (async @injected naming: `a_` prefix)

## Naming guidance

Use clear, unique, and contextual names. Recommended conventions:

- Feature-specific implementation:
  - `store_feature_x_data_to_influxdb`  (implementation tied to Feature X)
- Generic protocol name (independent of a concrete implementation):
  - `store_data_y`
- Specific implementation of a protocol:
  - `store_data_y__influxdb`
- Fully generic (not specific to any feature/protocol):
  - `store_influxdb`

Async `@injected` functions must use the `a_` prefix (enforced by another rule), for example:
- `a_store_data_y__influxdb`

## Bad

```py
from pinjected import injected, instance

@injected
def store_data():
    ...

@instance
def store_data():
    ...
```

```py
from pinjected import injected

@injected
async def store_data():
    ...
# Even if this were unique, async should be prefixed:
# a_store_data()
```

This will raise PINJ062 for the duplicate name (`store_data`).

## Good

```py
from pinjected import injected, instance

@injected
def store_data__influxdb():
    ...

@instance
def store_data__bigquery():
    ...
```

```py
from pinjected import injected

@injected
async def a_store_data__influxdb():
    ...
```

These use unique names and, for async, the required `a_` prefix.
