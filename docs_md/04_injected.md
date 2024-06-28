
# class Injected
`Injected` is a python object that represents a variable that requires injection.
It has a set of dependencies that are required to be created, and a provider function that creates the variable.
```python
from pinjected.di.util import Injected
from pinjected import Design
def provide_ab(a:int,b:int):
    return a+b
# Injected.bind can convert a provider function to an Injected object.
# the names of arguments are used as dependencies.
injected:Injected[int] = Injected.bind(provide_ab)
design = instances(
    a=1,
    b=2
)
assert design.to_graph()[injected] == 3
```


## Injected composition
### map
You can map an Injected to create another injected instance.
```python
from pinjected.di.util import Injected,instances
from pinjected import Design
design:Design = instances(
    a=1,
)
a:Injected[int] = Injected.by_name('a')
b:Injected[int] = a.map(lambda x:x+1) # must be a + 1
g = design.to_graph()
assert g[a] + 1  == g[b]
```

### zip/mzip
You can combine multiple injected instances into one.
The dependencies of the new Injected will be the union of the dependencies of the original Injected.
```python
from pinjected.di.util import Injected
from pinjected import Design
def provide_ab(a:int,b:int):
    return a+b
design = instances(
    a=1,
    b=2
)
g = design.to_graph()
# you can use getitem to get the value of Injected by key
assert g['a'] == 1
assert g['b'] == 2
a = Injected.by_name('a')
b = Injected.by_name('b')
c = a.map(lambda x:x+2)
abc = Injected.mzip(a,b,c)
ab_zip = Injected.zip(a,b) # use mzip if you need more than 2 Injected
assert g[abc] == (1,2,3)
assert g[ab_zip] == (1,2)
```

### dict/list
since we have map and zip, we can create dict and list from pinjected.
```python
from pinjected.di.util import Injected,instances
design = instances(
    a=1,
    b=2
)
a = Injected.by_name('a')
b = Injected.by_name('b')
c = a.map(lambda x:x+2)
injected_dict:Injected[dict] = Injected.dict(a=a,b=b,c=c) # == {'a':1,'b':2,'c':3}
injected_list:Injected[list] = Injected.list(a,b,c) # == [1,2,3]
```

## Partial Injection
Now the fun part begins. we can partially inject a function to receive some of its arguments from DI.
This turns a Callable into Injected[Callable].
The separation between the arguments meant to be injected and the arguments that are not meant to be injected is
done by a `/` in the argument list. So all the positional-only arguments become the dependencies of the Injected.

```python
from pinjected.di.util import Injected, instances
from pinjected import injected
from typing import Callable


@injected
def add(a: int, b: int, /, c: int):
    # a and b before / gets injected.
    # c must be provided when calling the function.
    return a + b + c


design = instances(
    a=1,
    b=2,
)
add_func: Injected[Callable[[int], int]] = add
total: Injected[int] = add(c=3)  # can be add_func(c=3) or add_func(3) or add(3)
g = design.to_graph()
assert g[total] == 6
assert g[add(3)] == 6
assert g[add](3) == 6
```

## Constructing a tree of injected
We can also form a syntax tree of injected functions, to create another injected instance.

```python
from pinjected.di.util import Injected, instances
from pinjected import injected
from typing import Callable


@injected
def x(logger, /, a: int):
    logger.info("x called")
    return a + 1


@injected
def y(logger, database_connection, /, x: int):
    logger.info(f"y called with x, using {database_connection}")
    return x + 1


x_andthen_y: Injected[int] = y(x(0))
design = instances(
    logger=print,
    database_connection="dummy_connection"
)
g = design.to_graph()
assert g[x_andthen_y] == 2
assert g[y(x(0))] == 2
```

This means that we can chain as many injected functions as we want, and the dependencies will be resolved automatically.

## Using Injected as a provider
Injected can be used as a provider function in a design.

```python
from pinjected.di.util import Injected, instances, providers, Design
from pinjected import injected, instance


@instance
def d_plus_one(d):
    return d + 1


# you can use instance as decorator when you don't need any non_injected arguments.
# now get_d_plus_one is Injected[int], so an integer will be created when it is injected by DI.
# don't forgeet to add slash in the argument list, or the arguments will not be injected.
@injected
def calc_d_plus_one(d: int, /, ):
    return d + 1


# you can use injected as decorator when you need non_injected arguments.
# if you don't provide non_injected arguments, it will a injected function that does not take any arguments when injected.
# now get_d_plus_one is Injected[Callable[[],int]], so a callable will be created when it is injected by DI.

d = instances(
    a=1,
    b=2
) + providers(
    c=lambda a, b: a + b,
    d=Injected.by_name('a').map(lambda x: x + 1),
    e=d_plus_one,
    get_e=calc_d_plus_one,
)
g = d.to_graph()
g['d'] == 2
g['e'] == 3
g['get_e']() == 4  # get_e ends up as a callable.
```

## Overriding Provider Function with Injected
Suppose you have a provider function already as follows:
```python
def provide_c(a,b):# you dont have to prefix this function name with "provide", but I suggest you use some naming convention to find this provider later on.
    return a+" "+b

d = instances(
    a = "my",
    b = "world"
) + providers(
    c=provide_c
)
```
but you want to override the provider function to use a specific value rather than a value from DI.
You can do as follows:
```python
from pinjected.di.util import Injected
overriden:Injected = Injected.bind(provide_c,a=Injected.pure("hello"))
d2 = d + providers(
    c= overriden
)
d.provide("c") == "my world"
d2.provide("c") == "hello world"
```
so that "a" can be manually injected only for "c".
Injected.bind takes a function and kwargs. kwargs will be used for overriding the parameter of given function.
Overriding value must be an instance of Injected. For pure instance, use Injected.pure. If you want to give a provider function to be used for the function, use Injected.bind.
```python
injected_c = Injected.bind(provide_c,
              a = Injected.bind(lambda b:b+"nested"),#you can nest injected
              b = "a" # this will make dependency named 'a' to be injected as 'b' for provide_c.
              ) # you can nest Injected
```

## Injected is a Functor
```python
Injected is an abstraction of data which require dependencies to be used inside DI.
# you can map an Injected instance to return different value after its computation.
a = Injected.pure("a") # gives "a" when used
b = a.map(lambda x:x*2) # gives "aa" when used
# you can map as many times as you want.
providers(
    a = a
).provide("a") == "a"
providers(
    a = b
).provide("a") == "aa"
```