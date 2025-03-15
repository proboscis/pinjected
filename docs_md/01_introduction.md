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
This make all the codes depend on the configuration file, requiring to have 'cfg' as an argument.
As a result, all the codes heavily depend on the structure of a cfg, and becomes impossible to be used without a cfg object.
This makes it hard to reuse the code, and makes it hard to change the structure of the code too. 
Also, simple testing becomes hard because you need to write a object creation code with its configuration file for each component you want to test.
Moreover, we often see several hundred lines of [configuration parsing code combined with object creation code](https://github.com/CompVis/stable-diffusion/blob/21f890f9da3cfbeaba8e2ac3c425ee9e998d5229/main.py#L418). 
This makes the code hard to read and guess which part is actually doing the work.

# The Solution
Pinjected solves these problem by providing a way to create a final object without passing a configuration object to each object creation function.
Instead, this library will automatically create all the dependencies and compose them to create the final object following the dependency graph.
The only thing you need to do is to define a dependency graph and a way to create each object.
This library will take care of the rest.

This library also provides a way to modify and combine dependency graphs, so that hyperparameter management becomes easy and portable.
By introducing Single Responsibility Principle and Dependency Inversion Principle, the code becomes more modular and reusable.
To this end, this library introduces a concept of Design and Injected object. Design is a collection of object providers with dependencies.
Injected object is an abstraction of object with dependencies, which can be constructed by a Design object.

# Use Case
So, how is that useful to machine learning experiments? Here's an example.

Let's start from a typical machine learning code. (You don't have to understand the code below, please just look at the structure.)

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
    loss:Callable
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

```
And configuration parsers:
```python
       
def get_optimizer(cfg:dict,model):
    if cfg['optimizer'] == 'Adam':
        return Adam(lr=cfg['learning_rate'],model.get_parameters())
    elif cfg['optimizer'] == 'SGD':
        return SGD(lr=cfg['learning_rate'],model.get_parameters())
    else:
        raise ValueError("Unknown optimizer")

def get_dataset(cfg:dict):
    if cfg['dataset'] == 'MNIST':
        return MNISTDataset(cfg['batch_size'],cfg['image_w'])
    elif cfg['dataset'] == 'CIFAR10':
        return CIFAR10Dataset(cfg['batch_size'],cfg['image_w'])
    else:
        raise ValueError("Unknown dataset")
    
def get_loss(cfg):
    if cfg['loss'] == 'MSE':
        return MSELoss(lr=cfg['learning_rate'])
    elif cfg['loss'] == 'CrossEntropy':
        return CrossEntropyLoss(lr=cfg['learning_rate'])
    else:
        raise ValueError("Unknown loss")
    
def get_saver(cfg):
    if cfg['saver'] == 'Local':
        return Saver(LocalIo())
    elif cfg['saver'] == 'MongoDB':
        return Saver(MongoDBIo())
    else:
        raise ValueError("Unknown saver")

def get_loader(cfg):
    if cfg['loader'] == 'Local':
        return Loader(LocalIo())
    elif cfg['loader'] == 'MongoDB':
        return Loader(MongoDBIo())
    else:
        raise ValueError("Unknown loader")
def get_model(cfg):
    if cfg['model'] == 'SimpleCNN':
        return SimpleCNN(cfg)
    elif cfg['model'] == 'ResNet':
        return ResNet(cfg)
    else:
        raise ValueError("Unknown model")
    
def get_trainer(cfg):
    model = get_model(cfg),
    return Trainer(
        model=model,
        optimizer = get_optimizer(cfg,model),
        loss = get_loss(cfg),
        dataset = get_dataset(cfg),
        saver = get_saver(cfg),
        model_identifier = cfg['model_identifier']
    )

def get_evaluator(cfg):
    return Evaluator(
        dataset = get_dataset(cfg),
        model_identifier = cfg['model_identifier'],
        loader = get_loader(cfg)
    )

def build_parser():
    """
    very long argparse code which needs to be modified everytime configuration structure changes
    """

if __name__ == "__main__":
    # can be argparse or config.json
    # cfg:dict = json.loads(Path("config.json").read_text())
    # cfg = build_parser().parse_args()
    cfg = dict(
        optimizer = 'Adam',
        learning_rate = 0.001,
        dataset = 'MNIST',
        batch_size = 128,
        image_w = 256,
        loss = 'MSE',
        saver = 'Local',
        loader = 'Local',
        model = 'SimpleCNN',
        model_identifier = 'model1'
    )
    trainer = get_trainer(cfg)
    trainer.train()
```
This code first loads a configuration via file or argparse.
(Here the cfg is constructed manually for simplicity.)

Then it creates all the objects and composes them to create a final object using a cfg object.
The problem we see are as follows:

1. Config Dependency:
   - All the objects depend on the cfg object, which makes it hard to reuse the code. 
   - The cfg object will get referenced deep inside the code, such as a pytorch module or logging module.
   - The cfg object often gets referenced not only in the constructor, but also in the method to change the behavior of the object.
2. Complicated Parser: 
   - The parser for config object gets quite long and complicated as you add more functionalities 
   - We see a lot of nested if-else statements in the code.
   - It is impossible to track the actual code block that is going to run due to nested if-else statements.
3. Manual Dependency Construction: 
   - The object dependency must be constructed manually and care must be taken to consider which object needs to be created first and passed.
   - When the dependency of an object changes, the object creation code must be modified. 
     - (suppose the new loss function suddenly wants to use the hyperparameter of the model, you have to pass the model to get_model() function!)
     

Instead, we can use Pinjected to solve these problems as follows:
```python
from dataclasses import dataclass
from pinjected import design,injected,instance

@instance
def optimizer__adam(learning_rate,model):
    return Adam(lr=learning_rate,model.get_parameters())
@instance
def dataset__mydataset(batch_size,image_w):
    return MyDataset(batch_size,image_w)
@instance
def model__sequential():
    return Sequential()
@instance
def loss__myloss():
    return MyLoss()

conf:Design = design(
    learning_rate = 0.001,
    batch_size = 128,
    image_w = 256,
    optimizer = optimizer__adam,
    dataset = dataset__mydataset,
    model = model__sequential,
    loss = loss__myloss,
    io_interface = LocalIo # use local file system by default
)

g = conf.to_graph()
#lets see model structure
print(g['model'])
# now lets do training
g[Trainer].train()
# lets evaluate
g[Evaluator].evaluate()
```
Let's see how the code above solves the problems we mentioned earlier.
1. Config Dependency: 
   - All the objects are created without depending on the cfg object.
   - Design object serves as a configuration for constructing the final object.
   - Each object is only depending on what the object needs, not the whole configuration object.
   - Each object can be tested with minimum configuration.
     - For example, dataset object can be tested with only batch_size and image_w.
2. Complicated Parser:
   - The parser is replaced with a simple function definition.
   - The function definition is simple and easy to understand.
   - The actual code block that is going to run is clear. 
   - No nested if-else statements.
   - No string parsing to actual implementation. Just pass the implementation object.
3. Manual Dependency Construction -> Automatic Dependency Construction:
   - The object dependency is constructed automatically by Pinjected.
   - The object dependency is resolved automatically by Pinjected.
   - When the dependency of an object changes, the object creation code does not need to be modified.
     - (suppose the myloss function suddenly wants to use the hyperparameter of the model, you only need to change the signature of loss__myloss to accept model/hyperparameter as an argument.)
```python
#Example of changing the loss function to use model hyperparameter
@instance
def loss_myloss2(model):
    return MyLoss(model.n_embeddings)
```

This doesnt look useful if you have only one set of configuration,
but when you start playing with many configurations,
this approach really helps like this.

```python
conf = design(
    learning_rate = 0.001,
    batch_size = 128,
    image_w = 256,
    optimizer = provide_optimizer,
    dataset = provide_dataset,
    model = provide_model,
    loss_calculator = provide_loss_calculator,
    io_interface = LocalIo # use local file system by default
)


conf_lr_001 = conf + design(# lets change lr
    learning_rate=0.01
)
conf_lr_01 = conf + design(
    learning_rate=0.1
)
lstm_model = design( # lets try LSTM?
    model = lambda:LSTM()
)
save_at_mongo = design( # lets save at mongodb
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
my_new_training_strategy = design(
    trainer=AtariTrainer
)
conf_extreme=conf_lr_01_mongo + my_new_training_strategy
g = conf_extreme.to_graph()
g["trainer"].train()# note the argument to 'provide' method can be a type object or a string.
```
as you can see, now you can do training with new AtariTrainer without modifying the existing code at all.
Furthermore, the old configurations are still completely valid to be used.
If you dont like the fact some code pieces are repeated from original Trainer, you can introduce an abstraction for that using generator or reactive x or callback.

[Next: Design](02_design.md)