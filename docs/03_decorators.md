## @instance and @injected Decorators

Pinjected provides two decorators for defining provider functions: `@injected` and `@instance`. While both decorators are used to create objects within the dependency injection framework, they have distinct behaviors and use cases.

### @instance
The @instance decorator is used to define a provider function that takes only injected arguments. All the arguments are considered injected and will be resolved by Pinjected.

When using @instance, Pinjected will resolve them based on the dependency graph. The decorated function will directly return the created object, without requiring any further invocation.

Note: Objects created with @instance are singleton-like within the same object graph (g). This means that for a given set of injected arguments, the @instance decorated function will be called only once, and the same instance will be reused for subsequent requests within the same g.

Here's an example:

```python
@instance
def train_dataset(logger,train_cfg):
  logger.info(f"Creating train_dataset with {train_cfg.dataset}. This is only called once.")
  # note a logger can be injected as well
  return get_dataset(train_cfg.dataset)

@instance
def logger():
    from loguru import logger
    return logger


# Usage
design:Design = instances(
    train_cfg = dict(dataset='dummy')
) + providers(
    logger=logger
)

g = design.to_graph()
dataset_1 = g['train_dataset'] # dataset is only created once for a g.
dataset_2 = g['train_dataset'] # the same dataset is returned
assert id(dataset_1) == id(dataset_2), "dataset_1 and dataset_2 should be the same object"
assert id(g['train_cfg']) == id(g['train_cfg']), "train_cfg should be the same object"
```

### @injected

The `@injected` decorator is used to define a provider function that takes both injected and non-injected arguments. 
It allows you to create a function that require some dependencies to be resolved by Pinjected,
while also accepting additional arguments that need to be provided explicitly.
In other words, '@injected' allows you to provide a function instead of a value.

When using `@injected`, you separate the injected and non-injected arguments using the `/` symbol. The arguments before the `/` are considered injected and will be resolved by Pinjected based on the dependency graph. The arguments after the `/` are non-injected and need to be provided when invoking the returned function.

Here's an example:

```python
@injected
def train_loader(train_dataset, train_cfg, /, batch_size):
  return DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=train_cfg.num_workers,
                    drop_last=train_cfg.drop_last)

@injected
def trainer(model, train_loader, /, epochs):
  train_loader:Callable[[int],DataLoader] # here train_loader is a function that only takes 'batch_size'.
  for epoch in range(epochs):
    for batch in train_loader(batch_size=32):
      # Training loop
      ...

# Usage
design = providers(
  train_dataset=train_dataset,
  train_cfg=train_cfg,
  model=model,
)

trainer_fn:Callable[[int],None] = design.provide(trainer)
# Now you can call the trainer_fn with the non-injected argument 'epochs'
trainer_fn(epochs=10)
```

In this example, train_dataset, train_cfg, and model are injected arguments, 
while batch_size and epochs are non-injected arguments. 
The trainer function takes model and train_loader as injected arguments, and epochs as a non-injected argument.

Note that the name of the decorated function train_loader is implicitly added to the design, 
allowing it to be used as an injected argument in the trainer function.
Inside the trainer function, train_loader is invoked with the non-injected argument batch_size to obtain the actual data loader instance. 
The training loop then uses the data loader to iterate over the batches and perform the training process.

To use the trainer function, you create a Design object and bind the necessary instances (train_dataset, train_cfg, and model). 
Then, you can call design.provide(trainer) to obtain the trainer_fn function. 
Finally, you invoke trainer_fn with the non-injected argument epochs to start the training process.

### Choosing Between @injected and @instance
The choice between @injected and @instance depends on your specific use case and the nature of the provider function.

Use @injected when you have a provider function that requires both injected and non-injected arguments. It provides flexibility to accept additional arguments that are not part of the dependency graph.
Use @instance when you have a simple provider function that only depends on injected arguments. It is a more concise way to define provider functions that don't require any additional invocation.
By leveraging these decorators appropriately, you can define provider functions that align with your dependency injection needs and create objects with the desired level of flexibility and simplicity.

[Next: Injected](04_injected.md)