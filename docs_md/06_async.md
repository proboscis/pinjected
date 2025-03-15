
# AsyncIO support
pinjected supports using async functions as a provider. For async providers, each dependencies are gathered in parallel, and the provider function is called in an async context.
```python
from pinjected import design, injected, instance
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


d = design(
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
from pinjected import design, injected, instance
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

d = design()
g = d.resolver()

assert (await g[y]) == 2
assert (await g[z]) == 3


```


