
# Design in Pinjected
The Design class is a fundamental concept in Pinjected that allows you to define and compose dependency injection configurations. It provides a flexible way to specify bindings for objects and their dependencies.
Adding Bindings
You can create a Design by combining different types of bindings:
```python 
from pinjected import instances, providers, classes
from dataclasses import dataclass


@dataclass
class DepObject:
    a: int
    b: int
    c: int
    d: int


@dataclass
class App:
    dep: DepObject


def run(self):
    print(self.dep.a + self.dep.b + self.dep.c + self.dep.d)


d = instances(
    a=0,
    b=1
) + providers(
    c=lambda a, b: a + b,
    d=lambda a, b, c: a + b + c
) 
```
In this example, we create a Design by combining:

- instances(): Binds concrete values
- providers(): Binds functions that provide values
- classes(): Binds classes to be instantiated
  
## Resolving Dependencies
To resolve dependencies and create objects based on a Design, you can use the to_graph() method.
It returns an object graph that allows you to access the resolved objects. 
```python
g = d.to_graph()
app = g['app']
```
The graph resolves all the dependencies recursively when ['app'] is required.

# instances()

instances() is a function to create a Design with instances. 
The value is bound to the key, and its value is used as a provider.

# providers()
providers() is a function to create a Design with providers.
A providers are meant to be invoked lazily when the value is needed.

A provider is one of the following types: [a callable, an Injected, an IProxy]. 
## a callable:
A callable can be used as a provider. 
When a callable is set as a provider, its argument names are used as the key for resolving dependencies.
```python
from pinjected import providers, instances
d = providers(
    a=lambda: 1,
    b=lambda a: a + 1
)
g = d.to_graph()
assert g['a'] == 1
assert g['b'] == 2
```

## an Injected
An Injected can be used as a provider. 
When an Injected is set as a provider, it is resolved by the DI.
```python
from pinjected import providers, instances, Injected
d = instances(
    a = 1
)+providers(
    b=Injected.bind(lambda a: a+1)
)
g = d.to_graph()
assert g['b'] == 2
```
Please read more about Injected in the [Injected section](docs_md/04_injected).

## an IProxy
An IProxy can be used as a provider. 
When an IProxy is set as a provider, it is resolved by the DI.
```python
from pinjected import providers, instances, injected, IProxy


@injected
def b(a: int, /):
    return a + 1


b: IProxy
d = instances(
    a=1
) + providers(
    b=b
)
g = d.to_graph()
assert g['b'] == 2

```
When @injected or @instance is used, the decorated function becomes an instance of IProxy.
IProxy can be composed with other IProxy or Injected to create a new IProxy easily.

Please refer to the [IProxy section](docs_md/04_injected_proxy) for more information.

# classes()
classes() is a function to create a Design with classes. However, currently the implementation is completely the same as providers().
A class is a callable and can be used as a provider. 




