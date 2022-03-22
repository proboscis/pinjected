# Pinject-Design

Pinject-Design is a wrapper library for [pinject](https://github.com/google/pinject).

## Why wrap Pinject?

Although pinject is a good library for dependency injection, the style it provides for specifying dependency binding was
tiring to write.

```python
# Original pinject:
import pinject
from dataclasses import dataclass
@dataclass
class SomeClass(object):
    foo:str
    bar:str

class MyBindingSpec(pinject.BindingSpec):
    def configure(self, bind):
        bind('foo', to_instance='a-foo') #side-effect here
        bind('bar', to_instance='a-foo')
class MyBindingSpec2(pinject.BindingSpec):
    def configure(self, bind):
        bind('foo', to_instance='b-foo')


obj_graph = pinject.new_object_graph(binding_specs=[MyBindingSpec()])
some_class = obj_graph.provide(SomeClass)
print
some_class.foo
'a-foo'
```
## pinject-design version
```python
from pinject_design.di.util import Design
from dataclasses import dataclass
@dataclass
class SomeClass(object):
    foo:str
    bar:str

d = Design() # empty immutable bindings called Design
d1 = d.bind_instance( #new Design
    foo="a-foo",
    bar="a-bar"
)
d2 = d1.bind_instance( # creates new Design from d1 keeping all other bindings except overriden foo
    foo="b-foo" #override foo of d1
)
a = d1.to_graph().provide(SomeClass)
assert(a.foo == "a-foo")
b = d2.to_graph().provide(SomeClass)
assert(b.foo == "b-foo")

```
This library makes pinject's binding more portable and easy to extend.

# Installation
`pip install pinject-design`

# Examples

## Add bindings
```python
from pinject_design.di.util import Design
from dataclasses import dataclass
@dataclass
class DepObject:
    a:int
    b:int 
    c:int
    d:int
@dataclass
class App:
    dep:DepObject
    def run(self):
        print(self.dep.a+self.dep.b+self.dep.c+self.dep.d)
d = Design().bind_instance(
    a = 0,
    b = 1
).bind_provider(
    c = lambda a,b :a + b,
    d = lambda a,b,c:a+b+c
).bind_class(
    dep=DepObject
)
d.to_graph().provide(App).run()
```

## Overriding Provider Function with Injected
Suppose you have a provider function already as follows:
```python
def provide_c(a,b):# you dont have to prefix this function name with "provide", but I suggest you use some naming convention to find this provider later on.
    return a+" "+b
d = Design().bind_instance(
    a = "my",
    b = "world"
).bind_provider(
    c=provide_c
)
```
but you want to override the provider function to use a specific value rather than a value from DI.
You can do as follows:
```python
from pinject_design.di.util import Injected
overriden:Injected = Injected.bind(provide_c,a=Injected.pure("hello"))
d.to_graph().provide("c") == "my world"
d = d.bind_provider(
    c= overriden
)
d.to_graph().provide("c") == "hello world"
```
so that a can be manually injected only for "c".
Injected.bind takes a function and kwargs. kwargs will be used for overriding the parameter of given function.
Overriding value must be an instance of Injected. For pure instance, use Injected.pure. If you want to give a provider function to be used for the function, use Injected.bind.
```python
injected_c = Injected.bind(provide_c,
              a = Injected.bind(lambda b:b+"nested"),#you can nest injected
              b = "a" # this will make dependency named 'a' to be injected as 'b' for provide_c.
              ) # you can nest Injected
```