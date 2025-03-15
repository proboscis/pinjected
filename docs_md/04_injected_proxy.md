# IProxy

IProxy is a class to help easy programming with Injected objects. 
This class provides a direct way of composing multiple Injected objects and calling a Injected function to get a new IProxy object.
Essentially, IProxy is a proxy object for an Injected object to construct an AST to be parsed by the Design later.

## How to make an IProxy object
1. Use the `@instance` decorator to create an IProxy object.
```python
@instance
def test_value(dep):
    return "hello"

test_value:IProxy[str]
```

2. Use the `@injected` decorator to create an IProxy object.
```python
@instance
def test_func(dep,/,x:int):
    return x + 1

test_func:IProxy[Callable[[int],int]]
```

3. Use the .proxy attribute on Injected object
```python
test_inject:Injected[str] = Injected.pure('test')
test_proxy:IProxy[str] = test_inject.proxy
```

## How to use IProxy object
Identical to Injected object, IProxy object can be used with Design class.
```python
from pinjected import design, IProxy, Injected
d = design(
    x = Injected.pure('hello').proxy # same as passing Injected.pure('hello')
)

x_proxy:IProxy[str] = Injected.by_name('x').proxy

g = d.to_graph()
assert g['x'] == 'hello'
assert g[x_proxy] == 'hello' # proxy can be passed to g's __getitem__ method
```

## IProxy Composition
IProxy is a class to provide easy composition of Injected objects and functions without using tedeous 'map' and 'zip' functions.

Let's begin from the simple map/zip example.
```python
from pinjected import design, IProxy, Injected

x = Injected.pure(1)
x_plus_one = x.map(lambda x: x + 1)

assert design()[x_plus_one] == 2, "x_plus_one should be 2"
```
Now, with IProxy, this can be re-written as:
```python
from pinjected import design, IProxy, Injected
x = Injected.pure(1).proxy
x_plus_one = x + 1
assert design()[x_plus_one] == 2, "x_plus_one should be 2"
```
This is achieved by overridding the __add__ method of IProxy to create a new IProxy object.
We have implemented most of the magic methods to make this work, so we can do things like:
```python
from pinjected import design, IProxy, Injected
from pathlib import Path
from typing import Callable

fun = lambda x: x + 1

fun_proxy:IProxy[Callable[[int],int]] = Injected.pure(fun).proxy
call_res:IProxy[int] = fun_proxy(1)
call_res_plus_one:IProxy[int] = fun_proxy(1) + 1
anything:IProxy[int] = (fun_proxy(1) + fun_proxy(2)) / 2
cache_dir:IProxy[Path] = Injected.by_name("cache_dir").proxy
cache_subdir:IProxy[Path] = cache_dir / "subdir"

list_proxy:IProxy[list[int]] = Injected.pure([0,1,2]).proxy
list_item:IProxy[int] = list_proxy[1]


g = design(
    cache_dir=Path("/tmp")
).to_graph()

assert g[cache_subdir] == Path("/tmp/subdir"), "cache_subdir should be /tmp/subdir"
assert g[list_item] == 1, "list_item should be 1"
```

[Next: Running](./05_running.md)
