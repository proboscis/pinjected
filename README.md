# Pinjected

Pinjected is a dependency injection / dependency resolver library inspired by [pinject](https://github.com/google/pinject).

This library makes it easy to compose mutliple python objects to create a final object. 
When you request for a final object, this library will automatically create all the dependencies and compose them to create the final object.


# Installation
`pip install pinjected`

# Documentations
Please read the following for tutorials and examples.
For more specific api documentation, please look at [documentation](https://pinjected.readthedocs.io/en/latest/)

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
from pinjected import instances,providers,injected,instance,classes

@instance
def optimizer(learning_rate):
    return Adam(lr=learning_rate)
@instance
def dataset(batch_size,image_w):
    return MyDataset(batch_size,image_w)
@instance
def model():
    return Sequential()
@instance
def loss_calculator():
    return MyLoss()

conf = instances(
    learning_rate = 0.001,
    batch_size = 128,
    image_w = 256,
) + providers(
    optimizer = optimizer,
    dataset = dataset,
    model = model,
    loss_calculator = loss_calculator
) + classes(
    io_interface = LocalIo# use local file system by default
)

g = conf.to_graph()
#lets see model structure
print(g['model'])
# now lets do training
g[Trainer].train()
# lets evaluate
g[Evaluator].evaluate()
```
Note that no classes defined above depend on specific configuration object. This means they are portable and can be reused.
This doesnt look useful if you have only one set of configuration,
but when you start playing with many configurations,
this approach really helps like this.

```python
conf = instances(
    learning_rate = 0.001,
    batch_size = 128,
    image_w = 256,
) + providers(
    optimizer = provide_optimizer,
    dataset = provide_dataset,
    model = provide_model,
    loss_calculator = provide_loss_calculator
) + classes(
    io_interface = LocalIo# use local file system by default
)


conf_lr_001 = conf + instances(# lets change lr
    learning_rate=0.01
)
conf_lr_01 = conf + instances(
    learning_rate=0.1
)
lstm_model = providers( # lets try LSTM?
    model = lambda:LSTM()
)
save_at_mongo = classes( # lets save at mongodb
    io_interface = MongoDBIo
)
conf_lr_001_lstm = conf_lr_001 + lstm_model # you can combine two Design!
conf_lr_01_mongo = conf_lr_01 + save_at_mongo
for c in [conf,conf_lr_001,conf_lr_01,conf_lr_001_lstm,conf_lr_01_mongo]:
    g = c.to_graph()
    g[Trainer].train()
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
my_new_training_strategy = classes(
    trainer=AtariTrainer
)
conf_extreme=conf_lr_01_mongo + my_new_training_strategy
g = conf_extreme.to_graph()
g["trainer"].train()# note the argument to 'provide' method can be a type object or a string.
```
as you can see, now you can do training with new AtariTrainer without modifying the existing code at all.
Furthermore, the old configurations are still completely valid to be used.
If you dont like the fact some code pieces are repeated from original Trainer, you can introduce an abstraction for that using generator or reactive x or callback.

## Injected vs Instance Decorators

Pinjected provides two decorators for defining provider functions: `@injected` and `@instance`. While both decorators are used to create objects within the dependency injection framework, they have distinct behaviors and use cases.

### @injected

The `@injected` decorator is used to define a provider function that takes both injected and non-injected arguments. It allows you to create objects that require some dependencies to be resolved by Pinjected, while also accepting additional arguments that need to be provided explicitly.

When using `@injected`, you separate the injected and non-injected arguments using the `/` symbol. The arguments before the `/` are considered injected and will be resolved by Pinjected based on the dependency graph. The arguments after the `/` are non-injected and need to be provided when invoking the returned function.

Here's an example:

```python
@injected
def train_loader(train_dataset, train_cfg, /, batch_size):
  return DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=train_cfg.num_workers,
                    drop_last=train_cfg.drop_last)

@injected
def trainer(model, train_loader, /, epochs):
  for epoch in range(epochs):
    for batch in train_loader(batch_size=32):
      # Training loop
      ...

# Usage
design = Design() + instances(
  train_dataset=train_dataset,
  train_cfg=train_cfg,
  model=model,
)

trainer_fn = design.provide(trainer)
trainer_fn(epochs=10)
```

In this example, train_dataset, train_cfg, and model are injected arguments, while batch_size and epochs are non-injected arguments. The trainer function takes model and train_loader as injected arguments, and epochs as a non-injected argument.

Note that the name of the decorated function train_loader is implicitly added to the design, allowing it to be used as an injected argument in the trainer function. Inside the trainer function, train_loader is invoked with the non-injected argument batch_size to obtain the actual data loader instance. The training loop then uses the data loader to iterate over the batches and perform the training process.

To use the trainer function, you create a Design object and bind the necessary instances (train_dataset, train_cfg, and model). Then, you can call design.provide(trainer) to obtain the trainer_fn function. Finally, you invoke trainer_fn with the non-injected argument epochs to start the training process.

### @instance
The @instance decorator is used to define a provider function that takes only injected arguments. It is a simpler version of @injected where all the arguments are considered injected and will be resolved by Pinjected.

When using @instance, all the arguments of the decorated function are treated as injected, and Pinjected will resolve them based on the dependency graph. The decorated function will directly return the created object, without requiring any further invocation.

Note: Objects created with @instance are singleton-like within the same object graph (g). This means that for a given set of injected arguments, the @instance decorated function will be called only once, and the same instance will be reused for subsequent requests within the same g.

Here's an example:

```python
@instance
def train_dataset(train_cfg):
  return get_dataset(train_cfg.dataset)

@instance
def data_processor(train_dataset):
  processed_data = preprocess(train_dataset)
  return processed_data

# Usage
design = Design() + instances(
  train_cfg=train_cfg,
)

processed_data_instance = design.provide(data_processor)
```

In this example, train_cfg and train_dataset are injected arguments. The data_processor function takes train_dataset as an injected argument and performs some preprocessing on it.

To use the data_processor instance, you create a Design object and bind the necessary instance (train_cfg). Pinjected will automatically resolve the train_dataset dependency based on the train_cfg instance. Then, you can directly call design.provide(data_processor) to obtain the processed_data_instance.

### Choosing Between @injected and @instance
The choice between @injected and @instance depends on your specific use case and the nature of the provider function.

Use @injected when you have a provider function that requires both injected and non-injected arguments. It provides flexibility to accept additional arguments that are not part of the dependency graph.
Use @instance when you have a simple provider function that only depends on injected arguments. It is a more concise way to define provider functions that don't require any additional invocation.
By leveraging these decorators appropriately, you can define provider functions that align with your dependency injection needs and create objects with the desired level of flexibility and simplicity.

## Understanding @injected and @instance Decorators
When using the Pinjected library for dependency injection, it's essential to understand the difference between the @injected and @instance decorators to ensure correct object creation and dependency resolution.

@instance Decorator
Use the @instance decorator for provider functions that should create objects only once and reuse them within the same object graph.
Objects created with @instance are singleton-like within the same object graph, meaning that the decorated function will be called only once for a given set of injected arguments.
When referring to dependencies decorated with @instance within other provider functions, use them directly without invoking them as functions.
Example:

```python
@instance
def train_dataset(train_cfg):
    return get_dataset(train_cfg.dataset)

@instance
def train_loader(train_dataset, train_cfg):
    return DataLoader(train_dataset, batch_size=train_cfg.bs, ...)
 ```
### @injected Decorator
Use the @injected decorator for provider functions that take both injected and non-injected arguments.
The @injected decorator allows you to create objects that require some dependencies to be resolved by Pinjected, while also accepting additional arguments that need to be provided explicitly.
When using @injected, separate the injected and non-injected arguments using the / symbol in the function signature.
Functions decorated with @injected return a function that needs to be invoked with the non-injected arguments after the dependencies are resolved.
Example:
```python
@injected
def train_and_test(runner, train_cfg, test_cfg, /):
    runner.train(train_cfg)
    if test_cfg.need_test:
        runner.test(test_cfg)
```
By properly using @instance for provider functions that create objects only once and @injected for functions that require both injected and non-injected arguments, you can ensure correct object creation and dependency resolution in your Pinjected-based code.

## Add bindings

```python
import pinjected.main_imply
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


d = instances(
  a=0,
  b=1
) + providers(
  c=lambda a, b: a + b,
  d=lambda a, b, c: a + b + c
) + classes(
  dep=DepObject
)
pinjected.main_imply.run()
```

## Combine Multiple Designs
```python
d1 = instances(
    a=0
)
d2 = instances(
    b=1
)
d3 = instances(
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
d = providers(
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


# AsyncIO support
pinjected supports using async functions as a provider. For async providers, each dependencies are gathered in parallel, and the provider function is called in an async context.
```python
from pinjected import instances, providers, injected, instance
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


d = providers(
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
from pinjected import instances, providers, injected, instance
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

d = providers()
g = d.resolver()

assert (await g[y]) == 2
assert (await g[z]) == 3


```



# CLI Support
An Injected instance can be run from CLI with the following command.
```
python -m pinjected run <path of an Injected variable> <optional path of a Design variable> <Optional overrides for a design> --additional-bindings
```
- Variable Path: `your.package.var.name`
- Design Path: `your.package.design.name`
- Optional Overrides: `your.package.override_design.name`

## Example CLI Calls
```
python -m pinjected my.package.instance --name hello --yourconfig anystring
```
This CLI will parse any additional keyword arguments into a call of `instances` internally to be appended to the design running this injected instance.
Which is equivalent to running following script:
```
from my.package import instance
design = instances(
    name='dummy',
    yourconfig='dummy'
    ...
) + instances(
    name = 'hello',
    yourconfig = 'anystring'
)

design.provide(instance)

### Using Injected variable in CLI argument
We can use `{package.var.name}` to tell the cli that the additional bindings are to be imported from the specified path.

Example:
```python
# my.module2.py
from pinjected import instance
@instance
def load_hostname():
    import socket
    return socket.gethostname()
```
```python
# my.module.py
from pinjected import injected
@injected
def print_hostname(hostname):
    print(hostname)
```
```bash
python -m pinjected my.module.print_hostname --hostname my.module2.load_hostname
```

This is useful for switching complicated injected instances for running the target. The complicated injected instances can be trained ML models, etc.

Example2:
```
# some.llm.module.py
from pinjected import injected

@injected
def llm_openai(openai_api_key,/,prompt):
    return "call open ai api with prompt..."

@injected
def llm_azure(azure_api_key,/,prompt):
    return "call azure api with prompt..."

@injected
def llm_llama(llama_model_on_gpu,/,prompt):
    return llama_model_on_gpu(prompt,configs...)

@injected
def chat(llm,/,prompt):
    return llm(prompt)
```

```bash
python -m pinjected run some.llm.module.chat --llm="{some.llm.module.llm_openai}" "hello!"
```
Now we can switch llm with llm_openai, llm_azure, llm_llama... by specifying a importable variable path.



```
## __meta_design__
`pinjected run` reads __meta_design__ variables in every parent package of the target variable:
```
- some_package
  | __init__.py   <-- can contain __meta_design__
  | module1
  | | __init__.py <-- can contain __meta_design__
  | | util.py     <-- can contain __meta_design__
```
When running `python -m pinjected run some_package.module1.util.run`, all __meta_design__ in parent packages will be loaded and concatenated.
Which in this case results in equivalent to running the following script:
```python
meta_design = some_package.__meta_design__ + some_package.module1.__meta_design + some_package.module1.util.__meta_design__
overrides = meta_design['overrides']
default_design = import_if_exist(meta_design['default_design_path'])
g = (default_design + overrides).to_graph()
g[some_package.module1.util.run]
```

## .pinjected.py
Additionaly, we can place .pinjected.py file in the current directly or the home directory. a global variable named 'default_design' and 'overrides' will be automatically imported, then prepended and appended to the design before running the target.

This is convinient for specifying user specific injection variables such as api keys, or some user specific functions.


# IDE Support
By installing a plugin to IDE, you can directly run the Injected variable by clicking a `Run` button associated with the Injected variable declaration line inside IDE.
(Documentation Coming Soon for IntelliJ Idea)

# Dependency Graph Visualization
You can visualize the dependency graph of an Injected instance in web browser for better understanding of your program.
(Documentation Coming Soon)

# Picklability
Compatible with dill and cloudpickle as long as the bound objects are picklable.


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


# Advanced Features

## Running an injected variable from command line

### run

```bash
pinjected run 
```

### meta_run

### visualize


