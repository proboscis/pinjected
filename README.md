# Pinject-Design

Pinject-Design is a wrapper library for [pinject](https://github.com/google/pinject).
# Installation
`pip install pinject-design`
# Use Case
So, how is that useful to machine learning experiments? Here's an example.
```python
from dataclasses import dataclass
def provide_optimizer(learning_rate):
    return Adam(lr=learning_rate)
def provide_dataset(batch_size,image_w):
    return MyDataset(batch_size,image_w)
def provide_model():
    return Sequential()
def provide_loss_calculator():
    return MyLoss()
from abc import ABC,abstractmethod
class IoInterface(ABC): # interface for IO used by saver/loader
    @abstractmethod
    def save(self,object,identifier):
        pass
    @abstractmethod
    def load(self,identifier):
        pass
class LocalIo(IoInterface):pass
    # implement save/load locally
class MongoDBIo(IoInterface):pass
    # implement save/load with MongoDB
class Saver(ABC):
    io_interface : IoInterface
    def save(self,model,identifier:str):
        self.io_interface.save(model,identifier)
    
class Loader(ABC):
    io_interface : IoInterface # try to only depend on interface so that actual implementation can be changed later
    def load(self,identifier):
        return self.io_interface.load(identifier)

conf = Design().bind_instance(
    learning_rate = 0.001,
    batch_size = 128,
    image_w = 256,
).bind_provider(
    optimizer = provide_optimizer,
    dataset = provide_dataset,
    model = provide_model,
    loss_calculator = provide_loss_calculator
).bind_class(
    io_interface = LocalIo# use local file system by default
)

@dataclass
class Trainer: # try to keep a class as small as possible to keep composability. 
    model:Module
    optimizer:Optimizer
    loss_calculator:Callable
    dataset:Dataset
    saver:Saver
    model_identifier:str
    def train(self):
        while True:
            for batch in self.dataset:
                self.optimizer.zero_grad()
                loss = self.loss_calculator(self.model,batch)
                loss.backward()
                self.optimizer.step()
                self.saver.save(self.model,self.model_identifier)

@dataclass
class Evaluator:
    dataset:Dataset
    model_identifier:str
    loader:Loader
    def evaluate(self):
        model = self.loader.load(self.model_identifier)
        # do evaluation using loaded model and dataset
# create an object graph
g = conf.to_graph()
#lets see model structure
print(g.provide("model"))
# now lets do training
g.provide(Trainer).train()
# lets evaluate
g.provide(Evaluator).evaluate()
```
Note that no classes defined above depend on specific configuration object. This means they are portable and can be reused.
This doesnt look useful if you have only one set of configuration,
but when you start playing with many configurations,
this approach really helps like this.

```python
conf = Design().bind_instance(
    learning_rate = 0.001,
    batch_size = 128,
    image_w = 256,
).bind_provider(
    optimizer = provide_optimizer,
    dataset = provide_dataset,
    model = provide_model,
    loss_calculator = provide_loss_calculator
).bind_class(
    io_interface = LocalIo# use local file system by default
)


conf_lr_001 = conf.bind_instance(# lets change lr
    learning_rate=0.01
)
conf_lr_01 = conf.bind_instance(
    learning_rate=0.1
)
lstm_model = Design().bind_provider( # lets try LSTM?
    model = lambda:LSTM()
)
save_at_mongo = Design.bind_class( # lets save at mongodb
    io_interface = MongoDBIo
)
conf_lr_001_lstm = conf_lr_001 + lstm_model # you can combine two Design!
conf_lr_01_mongo = conf_lr_01 + save_at_mongo
for c in [conf,conf_lr_001,conf_lr_01,conf_lr_001_lstm,conf_lr_01_mongo]:
    g = c.to_graph()
    g.provide(Trainer).train()
```
The good thing is that you can keep old configurations as variables.
And modifications on Design will not break old experiments.
Use this Design and keeping classess as small as possible by obeying the Single Resposibility Principle.
Doing so should prevent you from rewriting and breaking code when implmenting new feature.
## Adding Feature Without Rewriting
If you come up with a mind to extremely change the training procedure without breaking old experiments, you can create a new class and bind it as a "trainer".
Suppose you come up with a brilliant new idea that making the model play atari_game during training might help training like so:
```python
class AtariTrainer:
    model:Module
    optimizer:Optimizer
    dataset:Dataset
    atari_game:AtariGame
    loss_calculator:Callable
    def train(self):
        for batch in self.dataset:
            # lets play atari_game so that model may learn something from it.
            self.optimizer.zero_grad()
            self.atari_game.play(self.model)
            loss = self.loss_calculator(self.model,batch)
            self.optimizer.step()
            # do anything
my_new_training_strategy = Design().bind_class(
    trainer=AtariTrainer
)
conf_extreme=conf_lr_01_mongo + my_new_training_strategy
g = conf_extreme.to_graph()
g.provide("trainer").train()# note the argument to 'provide' method can be a type object or a string.
```
as you can see, now you can do training with new AtariTrainer without modifying the existing code at all.
Furthermore, the old configurations are still completely valid to be used.
If you dont like the fact some code pieces are repeated from original Trainer, you can introduce an abstraction for that using generator or reactive x or callback.
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

## Combine Multiple Designs
```python
d1 = Design().bind_instance(
    a=0
)
d2 = Design().bind_instance(
    b=1
)
d3 = Design().bind_instance(
    b=0
)
(d1 + d2).provide("b") == 1
(d1 + d2 + d3).provide("b") == 0
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

# Injected is a Functor
```python
Injected is an abstraction of data which require dependencies to be used inside DI.
# you can map an Injected instance to return different value after its computation.
a = Injected.pure("a") # gives "a" when used
b = a.map(lambda x:x*2) # gives "aa" when used
# you can map as many times as you want.
Design().bind_provider(
    a = a
).provide("a") == "a"
Design().bind_provider(
    a = b
).provide("a") == "aa"
```

# Mapping with dependency
Sometimes you want to map an Injected with a function with dependency from DI.
For that you can use Injected.apply_injected_function.
```python
design = Design().bind_instance(
    a = "a",
    b = "b",
    X = 42 
)
c:Injected = Injected.bind(lambda a,b:a+b) # now c is a+b
# on second thought, I want c to be multiplied by X
def multiplier(X):# lets get X from DI
    def impl(item):
        return item*X
    return impl # return actual implementation using X
injected_func:Injected[Callable] = Injected.bind(multiplier)
c2:Injected = c.apply_injected_func(injected_func)
design.bind_provider(
    c = c2
).to_graph().provide("c") == "ab"*42
```
This is useful when your mapping function requires many dependencies.

