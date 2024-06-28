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
- Dependency Graph Visualization
- Run configuration creation for intellij idea
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