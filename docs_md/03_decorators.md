## @injected vs @instance Decorators

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
design = providers(
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
design:Design = instances(
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
