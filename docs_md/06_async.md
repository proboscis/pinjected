
# AsyncIO support
pinjected supports using async functions as a provider. For async providers, each dependencies are gathered in parallel, and the provider function is called in an async context.
```python
from pinjected import instances, providers, injected, instance
import asyncio


@instance
async def x():
    await asyncio.sleep(1)
    return 1


@injected
async def y_provider(x, /):
    # Note that we do not need to await x, because it is already awaited by the DI.
    await asyncio.sleep(1)
    return x + 1


@injected
async def y_user(y):
    # Here, we need to await y since injected y is an async function.
    return await y()


@instance
def non_async_x():
    # we can also combine non-async and async functions.
    return 1


d = providers(
    x=x,
    y=y_provider
)
g = d.to_graph()  # to_graph returns a blocking resolver that internally call asyncio.run to resolve the dependencies.
assert g['y'] == 2
async_g = d.to_resolver()  # to_resolver returns an async resolver that can be awaited.
assert (await async_g['y']) == 2
```

## AsyncIO support for Injected AST composition
```python
from pinjected import instances, providers, injected, instance
import asyncio


@instance
async def x():
    await asyncio.sleep(1)
    return 1


@instance
def alpha():
    return 1


@injected
async def slow_add_1(x, /):
    await asyncio.sleep(1)
    return x + 1


# we can construct an AST of async Injected instances.
y = slow_add_1(x)
# we can also combine non-async and async Injected variables 
z = y + alpha

d = providers()
g = d.resolver()

assert (await g[y]) == 2
assert (await g[z]) == 3


```

## Advanced Async Patterns
For more complex async scenarios and performance optimization, see the [Advanced Usage Guide](11_advanced_usage.md). Here are some additional patterns:

Note: The `@instance` decorator is meant for providing objects asynchronously (especially for initializing large or time-consuming resources), while `@injected` is used for general-purpose functions including tasks and logic. The examples below use `@injected` since they perform tasks rather than initialize resources.

### Parallel Task Execution
```python
from pinjected import instances, providers, injected, instance
import asyncio

@injected
async def heavy_task_1():
    """Simulate a CPU-intensive task"""
    await asyncio.sleep(2)
    return "result_1"

@injected
async def heavy_task_2():
    """Simulate an I/O-bound task"""
    await asyncio.sleep(1)
    return "result_2"

@injected
async def parallel_processor(heavy_task_1, heavy_task_2, /):
    """Tasks are automatically executed in parallel"""
    return f"{heavy_task_1}_{heavy_task_2}"

# The tasks will execute concurrently, taking ~2 seconds total
# instead of ~3 seconds if executed sequentially
d = providers(
    task1=heavy_task_1,
    task2=heavy_task_2,
    result=parallel_processor
)
async_g = d.to_resolver()
result = await async_g['result']  # "result_1_result_2"
```

### Error Handling
```python
from pinjected import instances, providers, injected, instance
import asyncio

@injected
async def fallback_value():
    return "fallback"

@injected
async def unreliable_service(fallback_value, /):
    try:
        await asyncio.sleep(1)
        raise ConnectionError("Service unavailable")
    except ConnectionError:
        return fallback_value

d = providers(
    fallback=fallback_value,
    service=unreliable_service
)
async_g = d.to_resolver()
result = await async_g['service']  # Uses fallback value
```


