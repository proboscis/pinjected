# PINJ026: a_ Prefixed Dependencies Should Not Use Any Type

## Overview

This rule ensures that `a_` prefixed dependencies in `@injected` functions with a protocol decorator parameter have proper type annotations instead of `Any`. The `a_` prefix convention is used for async dependencies in pinjected, and these should be properly typed with protocols or concrete types for better type safety.

## Rationale

When using the `a_` prefix convention for async dependencies in `@injected` functions with protocols:

1. **Type Safety**: Using `Any` defeats the purpose of having a protocol definition
2. **Documentation**: Proper types make it clear what interfaces the dependencies must implement
3. **Refactoring Safety**: Type checkers can catch breaking changes when dependencies are properly typed
4. **Consistency**: If a protocol is defined for the function, all dependencies should follow the type contract

## Examples

### ❌ Incorrect

```python
from pinjected import injected
from typing import Any

@injected(protocol=AAddMultiResLineartToDatasetV3Protocol)
async def a_add_multi_res_lineart_to_dataset_v3(
    a_batch_convert_target: Any,  # Bad: a_ prefixed dependency with Any type
    a_auto_cached_sketch_to_line_art: Any,  # Bad: a_ prefixed dependency with Any type
    auto_image: Any,  # OK: not a_ prefixed
    logger: Any,  # OK: not a_ prefixed
    /,
    base_dataset: TypedDataset[SegSample],
    features: Features,
    cache: AsyncCache,
    line_art_resolutions: tuple[int, ...] = (512, 1024, 2048),
    batch_size: int = 32,
    n_jobs: int = 4,
    monitor_memory: bool = True,
) -> MultiResLineArtResult:
    ...
```

### ✅ Correct

```python
from pinjected import injected
from typing import Protocol

class ABatchConvertTargetProtocol(Protocol):
    async def convert(self, data: Any) -> Any: ...

class AAutoCachedSketchToLineArtProtocol(Protocol):
    async def process(self, sketch: Any) -> Any: ...

class AutoImageProtocol(Protocol):
    def get_image(self) -> Any: ...

class LoggerProtocol(Protocol):
    def info(self, msg: str) -> None: ...

@injected(protocol=AAddMultiResLineartToDatasetV3Protocol)
async def a_add_multi_res_lineart_to_dataset_v3(
    a_batch_convert_target: ABatchConvertTargetProtocol,  # Good: proper protocol type
    a_auto_cached_sketch_to_line_art: AAutoCachedSketchToLineArtProtocol,  # Good: proper protocol type
    auto_image: AutoImageProtocol,  # Good: proper type (though not a_ prefixed)
    logger: LoggerProtocol,  # Good: proper type (though not a_ prefixed)
    /,
    base_dataset: TypedDataset[SegSample],
    features: Features,
    cache: AsyncCache,
    line_art_resolutions: tuple[int, ...] = (512, 1024, 2048),
    batch_size: int = 32,
    n_jobs: int = 4,
    monitor_memory: bool = True,
) -> MultiResLineArtResult:
    ...
```

## How to Fix

1. Define protocol classes for each `a_` prefixed dependency
2. Replace `Any` type annotations with the appropriate protocol or concrete type
3. Ensure the protocol matches the expected interface of the dependency

Example transformation:
```python
# Before
@injected(protocol=SomeProtocol)
async def a_process_data(
    a_fetcher: Any,
    a_processor: Any,
    /,
    data: str
) -> Result:
    result = await a_fetcher.fetch(data)
    return await a_processor.process(result)

# After
from typing import Protocol

class AFetcherProtocol(Protocol):
    async def fetch(self, data: str) -> dict: ...

class AProcessorProtocol(Protocol):
    async def process(self, data: dict) -> Result: ...

@injected(protocol=SomeProtocol)
async def a_process_data(
    a_fetcher: AFetcherProtocol,
    a_processor: AProcessorProtocol,
    /,
    data: str
) -> Result:
    result = await a_fetcher.fetch(data)
    return await a_processor.process(result)
```

## Special Cases

This rule only applies to:
- Functions decorated with `@injected` that have a `protocol` parameter
- Dependencies (before `/`) that start with `a_` prefix
- Dependencies that are typed with `Any`

The rule does not apply to:
- `@instance` functions
- `@injected` functions without a protocol parameter
- Non `a_` prefixed dependencies
- Dependencies after the `/` separator

## Configuration

This rule can be disabled in your `pyproject.toml`:

```toml
[tool.pinjected-linter]
disable = ["PINJ026"]
```

## Severity

**Warning** - Using `Any` for `a_` prefixed dependencies reduces type safety but doesn't break functionality.

## See Also

- [PINJ017 - Missing Type Annotation for Dependencies](./pinj017_missing_dependency_type_annotation.md)
- [PINJ016 - Missing Protocol Parameter](./pinj016_missing_protocol.md)
- [Python Protocols Documentation](https://docs.python.org/3/library/typing.html#typing.Protocol)