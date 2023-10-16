# Pinjected

Pinjected is a dependency injection / dependency resolver library inspired by [pinject](https://github.com/google/pinject).

This library makes it easy to compose mutliple python objects to create a final object. 
When you request for a final object, this library will automatically create all the dependencies and compose them to create the final object.

# Installation
`pip install pinjected`

# Features
- Dependency Injection via Constructor
- Object Dependency Resolution
- Dependency Graph Visualization ... for Mac OS
- Run configuration creation for intellij idea ... Coming Soon
- CLI Support
- Functional Depndency Injection Composition

# The Problem
When you write a machine learning code, you often need to create a lot of objects and compose them to create a final object.
For example, you may need to create a model, a dataset, an optimizer, a loss calculator, a trainer, and an evaluator.
You may also need to create a saver and a loader to save and load the model.

Typically these objects creations are controlled by a configuration file like yaml.
A configuration file gets loaded at the top of code and passed to each object creation function.
This make all the codes depend on the configuration file, requring to have 'cfg' as an argument. 
As a result, all the codes heavily depend on the structure of a cfg, and becomes impossible to be used without a cfg object.
This makes it hard to reuse the code, and makes it hard to change the structure of the code too. Also, simple testing becomes hard because you need to write a object creation code with its configuration file for each component you want to test.

# The Solution
Pinjected solves this problem by providing a way to create a final object without passing a configuration object to each object creation function.
Instead, this library will automatically create all the dependencies and compose them to create the final object following the dependency graph.
The only thing you need to do is to define a dependency graph and a way to create each object.
This library will take care of the rest.

This library also provides a way to modify and combine dependency graphs, so that hyperparameter management becomes easy and portable. 
By introducing Single Responsibility Principle, and Dependency Inversion Principle, your code becomes more modular and reusable.
To this end, this library introduces a concept of Design, which is a collection of objects and their dependencies, 
and also Injected object, which models an object created by a Design.

# Use Case
So, how is that useful to machine learning experiments? Here's an example.

Let's start from a typical machine learning code.

```python
from dataclasses import dataclass

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
        
learning_rate = 0.001
batch_size = 128
image_w = 256
optimizer = Adam(lr=learning_rate)
dataset = MyDataset(batch_size,image_w)
model = Sequential()
loss = MyLoss()
saver = Saver(LocalIo())
loader = Loader(LocalIo())
trainer = Trainer(model,optimizer,loss,dataset,saver,"model1")
evaluator = Evaluator(dataset,"model1",loader)
trainer.train()
evaluator.evaluate()
```
Although the code is modular, it is hard to construct all the objects and compose them to create a final object.
Moreover, changing parameters and components requires to change the code itself, which makes it hard to reuse the code.

Instead, we offer a different approach that automatically composes objects from a design object.
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
Use this Design and keep classess as small as possible by obeying the Single Resposibility Principle.
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


# Examples

## Add bindings

```python

from pinjected import Design
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


d = Design().bind_instance(
    a=0,
    b=1
).bind_provider(
    c=lambda a, b: a + b,
    d=lambda a, b, c: a + b + c
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

# Object Graph
Our `Design.to_graph()` creates an object graph. This object graph controlls all the lifecycle of injected variables. 
Calling `g.provide("something")` asks the graph if "something" is already instantiated in the graph and retrieves it. 
If "something" was not instantiated, then "something" is instantiated along with its dependencies.

# Calling `provide` directly from Design
This will create a temporary short-lived object graph just for this `provide` call and returns its injection result.
Use this for debugging or factory purposes.
If you bind a function that returns a random value as a binding, calling the same Graph's `provide` should always 
return the same value, while Design's `provide` should return a random value for each invocation.
```python
import random
d = Design().bind_provider(
    r = lambda : random.uniform(0,1)
)
g = d.to_graph()
g.provide("r") == g.provide("r")
d.provide("r") != d.provide("r")# it is random. should rarely be the same.
```

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
design = Design().bind_instance(
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
design:Design = instances( # same as Design().bind_instance
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
design = Design().bind_instance(
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
from pinjected import injected_function
from typing import Callable


@injected_function
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
from pinjected import injected_function
from typing import Callable


@injected_function
def x(logger, /, a: int):
    logger.info("x called")
    return a + 1


@injected_function
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
from pinjected.di.util import Injected, instances, providers
from pinjected import injected_function, injected_instance


@injected_instance
def d_plus_one(d):
    return d + 1


# you can use injected_instance as decorator when you don't need any non_injected arguments.
# now get_d_plus_one is Injected[int], so an integer will be created when it is injected by DI.
# don't forgeet to add slash in the argument list, or the arguments will not be injected.
@injected_function
def calc_d_plus_one(d: int, /, ):
    return d + 1


# you can use injected_function as decorator when you need non_injected arguments.
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
from pinjected.di.util import Injected
overriden:Injected = Injected.bind(provide_c,a=Injected.pure("hello"))
d2 = d.bind_provider(
    c= overriden
)
d.provide("c") == "my world"
d2.provide("c") == "hello world"
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

## Injected is a Functor
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

# CLI Support
An Injected instance can be run from CLI with the following command.
```
python -m pinjected <path of a Injected variable> <path of a Design variable or null> <Optional overrides for a design>
```
- Variable Path: `your.package.var.name`
- Design Path: `your.package.design.name`
- Optional Overrides:
```
python -m pinjected my.package.injected_instance --name hello --yourconfig anystring
```
This CLI will parse any additional keyword arguments into a call of `instances` internally to be appended to the design running this injected instance.
Which is equivalent to running following script:
```
from my.package import injected_instance
design = instances(
    name='dummy',
    yourconfig='dummy'
    ...
) + instances(
    name = 'hello',
    yourconfig = 'anystring'
)

design.provide(injected_instance)
```
# IDE Support
By installing a plugin to IDE, you can directly run the Injected variable by clicking a `Run` button associated with the Injected variable declaration line inside IDE.
(Documentation Coming Soon for IntelliJ Idea)

# Dependency Graph Visualization
You can visualize the dependency graph of an Injected instance in web browser for better understanding of your program.
(Documentation Coming Soon)

# Picklability
Compatible with dill and cloudpickle as long as the bound objects are picklable.

# Rewriting the example in the beginning with injected_function

```python
from pinjected.di.util import Injected, instances, providers
from pinjected import injected_function, injected_instance
from dataclasses import dataclass


@injected_instance
def optimizer(learning_rate):
    return Adam(lr=learning_rate)


@injected_instance
def dataset(batch_size, image_w):
    return MyDataset(batch_size, image_w)


@injected_instance
def model():
    return Sequential()


@injected_instance
def loss_calculator():
    return MyLoss()


@injected_function
def save_local(local_dir, /, model, identifier):
    # save model locally
    pass


@injected_function
def load_local(local_dir, /, identifier):
    # load model locally
    pass


@injected_function
def save_mongodb(mongodb_conn, /, model, identifier):
    # save model to mongodb
    pass


@injected_function
def load_mongodb(mongodb_conn, /, identifier):
    # load model from mongodb
    pass


local_save_conf = providers(
    save=save_local,
    load=load_local,
) + instances(
    local_dir="/tmp"
)
mongodb_save_conf = providers(
    save=save_mongodb,
    load=load_mongodb
) + providers(
    mogndb_address="mongodb://localhost:27017",
    mongodb_conn=lambda mongodb_address: MongoClient(mogodb_address)
)

default_conf = instances(
    learning_rate=0.001,
    batch_size=128,
    image_w=256,
) + local_save_conf  # or use mongodb_save_conf


# now we don't need a trainer class.
@injected_function
def train(
        model: Module,
        optimizer: Optimizer,
        loss_calculator: Callable,
        dataset: Dataset,
        model_identifier: str,
        save: Callable[[Module, str], None],
        /
):
    while True:
        for batch in dataset:
            optimizer.zero_grad()
            loss = loss_calculator(model, batch)
            loss.backward()
            optimizer.step()
            save(model, model_identifier)


# no evaluator classes too.
@injected_function
def evaluate(
        model: Module,
        dataset: Dataset,
        model_identifier: str,
        load: Callable[[str], Module],
        /
):
    model = load(model_identifier)
    # do evaluation using loaded model and dataset


# create an object graph
g = default_conf.to_graph()
# lets see model structure
print(g.provide("model"))
# now lets do training
g[train]()
# lets evaluate
g[evaluate]()
```

# TODO
- add mnist training example with keras
- add 'modularization on the fly' example
- add dependency visualization example
- post Reddit
- post SHOW HN
- add gif demo

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
from pinjected import Design, instances, providers
from dataclasses import dataclass
@dataclass
class SomeClass(object):
    foo:str
    bar:str

d = Design() # empty immutable bindings called Design
d1 = instances( # new Design
    foo="a-foo",
    bar="a-bar"
)
d2 = d1 + instances( # creates new Design on top of d1 keeping all other bindings except overriden foo
    foo="b-foo" #override foo of d1
)
a = d1.to_graph()[SomeClass]
assert(a.foo == "a-foo")
b = d2.to_graph()[SomeClass]
assert(b.foo == "b-foo")

```
This library makes pinject's binding more portable and easy to extend.

# Visualization (Supported after 0.1.128)
Pinjected supports visualization of dependency graph.
```bash
pinjected run_injected visualize <full.path.of.Injected.variable> <full.path.of.Design.variable>
```
For example:
```bash
pinjected run_injected visualize pinjected.test_package.child.module1.test_viz_target pinjected.test_package.child.module1.viz_target_design
```
