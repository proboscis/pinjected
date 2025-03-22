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
d = design(
    r = Injected.bind(lambda : random.uniform(0,1))
)
g = d.to_graph()
g.provide("r") == g.provide("r")
d.provide("r") != d.provide("r") # it is random. should rarely be the same.
```

