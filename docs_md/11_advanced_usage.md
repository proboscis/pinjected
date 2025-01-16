# Advanced Usage Guide

This guide covers advanced topics and best practices for using Pinjected in complex scenarios, including async operations, performance optimization, and scaling considerations.

## Table of Contents
1. [Performance Optimization](#performance-optimization)
2. [Scaling and Resource Management](#scaling-and-resource-management)
3. [Advanced Async Patterns](#advanced-async-patterns)
4. [Complex Dependency Management](#complex-dependency-management)
5. [Best Practices](#best-practices)

## Performance Optimization

### Concurrency Strategies
When working with async dependencies, Pinjected automatically handles parallel resolution of dependencies. Here are some strategies to optimize performance:

```python
from pinjected import instances, providers, injected, instance
import asyncio

@instance
async def resource_pool():
    """Initialize a resource pool with optimal size"""
    pool_size = min(32, (os.cpu_count() or 1) * 4)
    return await create_resource_pool(size=pool_size)

@injected
async def worker(resource_pool, /):
    """Efficiently use resources from the pool"""
    async with resource_pool.acquire() as resource:
        return await process_with_resource(resource)

@instance
async def parallel_processor(worker):
    """Process multiple items concurrently with controlled resource usage"""
    tasks = [worker() for _ in range(10)]
    return await asyncio.gather(*tasks)
```

### Reducing Overhead
- Use `@instance` for singleton-like objects that should be reused
- Leverage `Design.to_graph()` for long-lived dependency graphs
- Avoid unnecessary provider recreation by moving providers outside loops

### Memory Management
- Use session scopes for temporary resources
- Clean up resources explicitly when no longer needed
- Monitor memory usage in large dependency graphs

## Scaling and Resource Management

### Handling Large Dependency Graphs
For applications with complex dependency structures:

```python
@injected
def complex_service(db_connection, cache_client, message_queue, /):
    """Example of a service with multiple dependencies"""
    return ServiceImplementation(
        db=db_connection,
        cache=cache_client,
        queue=message_queue
    )

# Group related dependencies
database = providers(
    connection_pool=db_connection_pool,
    primary=primary_connection,
    replica=replica_connection
)

cache = providers(
    client=redis_client,
    policy=cache_policy
)

# Compose larger systems
system = providers(
    database=database,
    cache=cache,
    service=complex_service
)
```

### Resource Lifecycle Management
- Initialize resources lazily using async providers
- Implement proper cleanup in async context managers
- Use dependency graphs for controlled resource sharing

### Monitoring and Debugging
- Track dependency resolution time
- Monitor resource usage
- Implement logging for complex dependency chains
- Use dependency graph visualization (see [Miscellaneous - Visualization](08_misc.md#visualization-supported-after-01128))
- Leverage IDE support for debugging (see [Miscellaneous - IDE Support](08_misc.md#ide-support))

## Advanced Async Patterns

### Parallel Dependency Resolution
```python
@instance
async def heavy_task_1():
    await asyncio.sleep(1)  # Simulate heavy work
    return "result_1"

@instance
async def heavy_task_2():
    await asyncio.sleep(1)  # Simulate heavy work
    return "result_2"

@injected
async def combined_result(heavy_task_1, heavy_task_2, /):
    """Dependencies are resolved in parallel automatically"""
    return f"{heavy_task_1}_{heavy_task_2}"
```

### Error Handling in Async Operations
```python
@injected
async def resilient_service(dependency, /):
    try:
        result = await dependency()
        return result
    except AsyncTimeout:
        return await fallback_strategy()
    except Exception as e:
        logger.error(f"Failed to resolve dependency: {e}")
        raise ServiceError("Service unavailable") from e
```

## Complex Dependency Management

### Circular Dependencies
Pinjected can detect circular dependencies at runtime. There are several strategies to handle circular dependencies:

1. Using Abstract Base Classes (Recommended)
   - Define interfaces to break tight coupling
   - Use dependency inversion principle
   - Implement concrete classes separately

2. Implementing Lazy Providers
   - Delay instantiation until needed
   - Break circular reference chains
   - Use factory patterns

3. Breaking Cycles with Design Patterns
   - Mediator pattern for complex interactions
   - Event-based communication
   - State management separation

Example using abstract base classes:
```python
from typing import Protocol, Any
from dataclasses import dataclass

# Define interfaces
class DataProcessorInterface(Protocol):
    def process(self, data: Any) -> Any: ...

class StorageInterface(Protocol):
    def store(self, data: Any) -> None: ...

# Implement concrete classes
@dataclass
class DataProcessor:
    storage: StorageInterface

    def process(self, data: Any) -> Any:
        result = self._transform(data)
        self.storage.store(result)
        return result

    def _transform(self, data: Any) -> Any:
        return f"processed_{data}"

@dataclass
class Storage:
    processor: DataProcessorInterface

    def store(self, data: Any) -> None:
        # Can safely call processor methods since we depend on interface
        self.processor.process(data)

# Provider functions
@injected
def create_processor(storage: StorageInterface, /) -> DataProcessorInterface:
    return DataProcessor(storage)

@injected
def create_storage(processor: DataProcessorInterface, /) -> StorageInterface:
    return Storage(processor)

# Configure with interfaces to break circular dependency
design = providers(
    processor=create_processor,
    storage=create_storage
).with_interfaces({
    'processor': DataProcessorInterface,
    'storage': StorageInterface
})
```

Example using lazy providers:
```python
from typing import Callable, Any
from functools import partial

# Break circular dependency with lazy initialization
@injected
def create_service_a(get_b: Callable[[], Any], /):
    """Service A depends on a function to get B instead of B directly"""
    return ServiceA(get_b)

@injected
def create_service_b(get_a: Callable[[], Any], /):
    """Service B depends on a function to get A instead of A directly"""
    return ServiceB(get_a)

# Configure with lazy providers
design = providers(
    service_a=create_service_a,
    service_b=create_service_b,
    get_a=partial(design.get, 'service_a'),
    get_b=partial(design.get, 'service_b')
)
```

### Dynamic Dependency Resolution
Pinjected supports dynamic dependency resolution and runtime provider configuration. This is useful for:
- Environment-specific implementations
- Feature toggles and A/B testing
- Plugin systems
- Runtime configuration changes

Here are some advanced patterns:

1. Context-Based Resolution:
```python
@injected
async def dynamic_provider(context, /):
    """Resolve dependencies based on runtime context"""
    if context.is_production:
        return await production_implementation()
    return await development_implementation()
```

2. Runtime Provider Registration:
```python
from typing import Dict, Any

class PluginRegistry:
    def __init__(self):
        self.plugins: Dict[str, Any] = {}

    def register(self, name: str, implementation: Any):
        self.plugins[name] = implementation

@instance
def plugin_registry():
    return PluginRegistry()

@injected
def plugin_provider(registry: PluginRegistry, plugin_name: str, /):
    """Dynamically provide plugins based on name"""
    return registry.plugins.get(plugin_name)

# Register plugins at runtime
design = providers(
    registry=plugin_registry,
    active_plugin=plugin_provider
).bind_provider(
    'plugin_name', lambda: 'custom_plugin'
)
```

3. Dynamic Configuration Override:
```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class Config:
    feature_flags: dict
    environment: str
    overrides: Optional[dict] = None

@instance
def base_config():
    return Config(
        feature_flags={'new_feature': False},
        environment='development'
    )

@injected
def feature_provider(config: Config, /):
    """Provide features based on config"""
    if config.overrides and 'new_feature' in config.overrides:
        return config.overrides['new_feature']
    return config.feature_flags['new_feature']

# Override configuration at runtime
design = providers(
    config=base_config,
    feature=feature_provider
)

# Later, update configuration:
design.bind_instance(
    'config',
    Config(
        feature_flags={'new_feature': False},
        environment='production',
        overrides={'new_feature': True}
    )
)
```

## Best Practices

### Code Organization
1. Group related providers in separate modules
2. Use clear naming conventions for providers
3. Document complex dependency relationships

### Error Handling
1. Implement proper error boundaries
2. Use meaningful error messages
3. Handle cleanup in error cases

### Testing
1. Use mock providers for testing
2. Test complex dependency graphs
3. Verify async behavior

### Performance Considerations
1. Profile dependency resolution time
2. Monitor memory usage
3. Implement proper resource cleanup

### Security
1. Validate input data
2. Handle sensitive information properly
3. Implement access controls

## See Also
- [Async Support Documentation](06_async.md) for basic async patterns and AsyncIO integration
- [Resolver Documentation](07_resolver.md) for dependency resolution details
- [Miscellaneous Documentation](08_misc.md) for visualization, IDE support, and other features
