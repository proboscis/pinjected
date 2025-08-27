# PINJ057: No Generic Type Annotations for Dependencies

## Rule Description

Dependencies in `@injected` functions must use Protocol types as type annotations, not generic types like `callable`, `Any`, or other non-Protocol types.

## Why This Rule Exists

Using generic types like `callable` or `Any` for dependencies:
1. **Loses type safety** - The type checker cannot verify that the dependency provides the expected interface
2. **Makes code harder to understand** - It's unclear what methods/attributes the dependency should have
3. **Prevents proper IDE support** - Auto-completion and type hints won't work properly
4. **Violates the principle of explicit interfaces** - Dependencies should have clearly defined contracts

## Common Violations

### Using `callable` type annotation

❌ **Bad:**
```python
from pinjected import injected

@injected
def process_data(
    fetch_data: callable,  # PINJ057: Generic 'callable' type
    store_data: callable,  # PINJ057: Generic 'callable' type
    /,
    data: str
) -> str:
    fetched = fetch_data()
    store_data(fetched)
    return fetched
```

✅ **Good:**
```python
from pinjected import injected
from typing import Protocol

class FetchDataProtocol(Protocol):
    def __call__(self) -> str: ...

class StoreDataProtocol(Protocol):
    def __call__(self, data: str) -> None: ...

@injected
def process_data(
    fetch_data: FetchDataProtocol,
    store_data: StoreDataProtocol,
    /,
    data: str
) -> str:
    fetched = fetch_data()
    store_data(fetched)
    return fetched
```

### Using `Any` type annotation

❌ **Bad:**
```python
from pinjected import injected
from typing import Any

@injected
def orchestrate(
    service: Any,  # PINJ057: Too generic
    processor: Any,  # PINJ057: Too generic
    /,
) -> None:
    service.serve()  # No type checking!
    processor.process()  # No type checking!
```

✅ **Good:**
```python
from pinjected import injected
from typing import Protocol

class ServiceProtocol(Protocol):
    def serve(self) -> None: ...

class ProcessorProtocol(Protocol):
    def process(self) -> None: ...

@injected
def orchestrate(
    service: ServiceProtocol,
    processor: ProcessorProtocol,
    /,
) -> None:
    service.serve()
    processor.process()
```

### Using non-Protocol class types

❌ **Bad:**
```python
from pinjected import injected

class DatabaseConnection:
    def query(self, sql: str) -> list: ...

@injected
def fetch_data(
    db: DatabaseConnection,  # PINJ057: Not a Protocol
    /,
    query: str
) -> list:
    return db.query(query)
```

✅ **Good:**
```python
from pinjected import injected
from typing import Protocol

class DatabaseProtocol(Protocol):
    def query(self, sql: str) -> list: ...

@injected
def fetch_data(
    db: DatabaseProtocol,
    /,
    query: str
) -> list:
    return db.query(query)
```

## Exceptions

The following types are allowed as they represent basic data types that don't typically need Protocol wrappers:
- `str`, `int`, `float`, `bool`, `bytes`
- `dict`, `list`, `tuple`, `set`
- `None`

Example of allowed basic types:
```python
@injected
def configure_service(
    config: dict,  # OK - basic type
    max_retries: int,  # OK - basic type
    enabled_features: list,  # OK - basic type
    /,
) -> None:
    pass
```

## Real-World Example

From the example in your request:

❌ **Bad:**
```python
@injected(protocol=AFetchAndStoreNewBloombergHeadlinesProtocol)
async def a_fetch_and_store_new_bloomberg_headlines(
    a_fetch_bloomberg_top_headlines: AFetchBloombergTopHeadlinesProtocol,  # Good
    a_store_raw_bloomberg_article: callable,  # PINJ057
    a_query_latest_stored_bloomberg_article_time: callable,  # PINJ057
    a_ensure_bloomberg_influxdb_bucket: callable,  # PINJ057
    a_emit_bloomberg_fetch_metrics: callable,  # PINJ057
    a_check_bloomberg_article_exists_by_id: callable,  # PINJ057
    /,
    source: str = "homepage_latest",
) -> int:
    pass
```

✅ **Good:**
```python
from typing import Protocol

class AStoreRawBloombergArticleProtocol(Protocol):
    async def __call__(self, article: dict) -> None: ...

class AQueryLatestStoredBloombergArticleTimeProtocol(Protocol):
    async def __call__(self) -> datetime: ...

class AEnsureBloombergInfluxdbBucketProtocol(Protocol):
    async def __call__(self) -> None: ...

class AEmitBloombergFetchMetricsProtocol(Protocol):
    async def __call__(self, metrics: dict) -> None: ...

class ACheckBloombergArticleExistsByIdProtocol(Protocol):
    async def __call__(self, article_id: str) -> bool: ...

@injected(protocol=AFetchAndStoreNewBloombergHeadlinesProtocol)
async def a_fetch_and_store_new_bloomberg_headlines(
    a_fetch_bloomberg_top_headlines: AFetchBloombergTopHeadlinesProtocol,
    a_store_raw_bloomberg_article: AStoreRawBloombergArticleProtocol,
    a_query_latest_stored_bloomberg_article_time: AQueryLatestStoredBloombergArticleTimeProtocol,
    a_ensure_bloomberg_influxdb_bucket: AEnsureBloombergInfluxdbBucketProtocol,
    a_emit_bloomberg_fetch_metrics: AEmitBloombergFetchMetricsProtocol,
    a_check_bloomberg_article_exists_by_id: ACheckBloombergArticleExistsByIdProtocol,
    /,
    source: str = "homepage_latest",
) -> int:
    pass
```

## Configuration

This rule cannot be disabled as it enforces a fundamental design principle of the pinjected framework.