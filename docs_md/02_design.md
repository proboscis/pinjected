
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


