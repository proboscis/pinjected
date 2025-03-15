
# Design in Pinjected
The Design class is a fundamental concept in Pinjected that allows you to define and compose dependency injection configurations. It provides a flexible way to specify bindings for objects and their dependencies.
Adding Bindings
You can create a Design by combining different types of bindings:
```python 
from pinjected import design
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


d = design(
    a=0,
    b=1,
    c=lambda a, b: a + b,
    d=lambda a, b, c: a + b + c,
    dep=Injected.bind(DepObject)
)
d2 = design( # same definition as the d. This automatically switches instances/providers/classes depending on the type of the object
    a=0,
    b=1,
    c=lambda a, b: a + b,
    d=lambda a, b, c: a + b + c,
    dep=Injected.bind(DepObject)
)
```
In this example, we create a Design using the design() function, which automatically handles different types of bindings based on the type of object:

- design(): Automatically categorizes bindings based on the type of the object:
  - Concrete values (previously handled by instances())
  - Functions that provide values (previously handled by providers())
  - Classes to be instantiated (previously handled by classes())
  - If the object is a class, it should be wrapped with Injected.bind() before binding
  - If the object is a callable function, it should be wrapped with Injected.bind() if it expects injected dependencies
  - If the object is an object that is not callable (i.e., no __call__ method), it is bound as an instance directly
  
## Resolving Dependencies
To resolve dependencies and create objects based on a Design, you can use the to_graph() method.
It returns an object graph that allows you to access the resolved objects. 
```python
g = d.to_graph()
app = g['app']
```
The graph resolves all the dependencies recursively when ['app'] is required.
Note that the graph instantiates objects lazily, meaning that objects are created only when they are needed.

# Using design() with different types of bindings

When using the design() function, the type of binding is automatically determined:

- **Constant values**: When a non-callable value is provided, it is bound directly to the key
- **Provider functions**: When a callable is provided, it is treated as a provider function
- **Classes**: When a class is provided, it is bound as a class to be instantiated

A provider is one of the following types: a `callable`, an `Injected` and an `IProxy`. 

## `callable`:
A callable can be used as a provider. 
When a callable is set as a provider, its argument names are used as the key for resolving dependencies.
```python
from pinjected import design
d = design(
    a=lambda: 1,
    b=lambda a: a + 1 # b is dependent on a
)
g = d.to_graph()
assert g['a'] == 1
assert g['b'] == 2 
```

## `Injected`
An Injected can be used as a provider. Injected is a python object that represents a variable that requires injection.
When an Injected is set as a provider, it is resolved by the DI.
```python
from pinjected import design, Injected
d = design(
    a = 1,
    b=Injected.bind(lambda a: a+1)
)
g = d.to_graph()
assert g['b'] == 2
```
Please read more about Injected in the [Injected section](docs_md/04_injected.md).

## `IProxy`
An IProxy can be used as a provider. 
When an IProxy is set as a provider, it is resolved by the DI.
```python
from pinjected import design, injected, IProxy


@injected
def b(a: int, /):
    return a + 1


b: IProxy
d = design(
    a=1,
    b=b
)
g = d.to_graph()
assert g['b'] == 2

```
When `@injected` or `@instance` is used, the decorated function becomes an instance of IProxy.
IProxy can be composed with other IProxy or Injected to create a new IProxy easily.

Please refer to the [IProxy section](docs_md/04_injected_proxy) for more information.

# Classes as providers
When a class is provided to the design() function, it should be wrapped with Injected.bind().
A class is a callable and can be used as a provider just like function providers, but must be properly wrapped.

```python
from pinjected import design, Injected

class MyService:
    def __init__(self, dependency1, dependency2):
        self.dependency1 = dependency1
        self.dependency2 = dependency2

# Correct way to bind a class
d = design(
    service=Injected.bind(MyService)
)
```

[Next: Injected](03_decorators.md)



