# Appendix
## Why not Pinject?

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
## Pinjected version
```python
from pinjected import Design, design
from dataclasses import dataclass
@dataclass
class SomeClass(object):
    foo:str
    bar:str

d:Design = design() # empty immutable bindings called Design
d1:Design = design( # new Design
    foo="a-foo",
    bar="a-bar"
)
d2:Design = d1 + design( # creates new Design on top of d1 keeping all other bindings except overriden foo
    foo="b-foo" #override foo of d1
)
a = d1.to_graph()[SomeClass]
assert(a.foo == "a-foo")
b = d2.to_graph()[SomeClass]
assert(b.foo == "b-foo")

```
This library makes pinject's binding more portable and easy to extend.