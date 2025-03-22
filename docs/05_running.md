# CLI Support

An Injected instance can be run from CLI with the following command.

```bash
python -m pinjected run [path of an Injected variable] [optional path of a Design variable] [Optional overrides for a design] --additional-bindings
```

- Variable Path: `your.package.var.name`
- Design Path: `your.package.design.name`
- Optional Overrides: `your.package.override_design.name`

## Example CLI Calls

```bash
python -m pinjected my.package.instance --name hello --yourconfig anystring
```

This CLI will parse any additional keyword arguments into a call of `design` internally to be appended to the design
running this injected instance.
Which is equivalent to running following script:

```python
from my.package import instance
d = design(
    name='dummy',
    yourconfig='dummy'
) + design(
    name = 'hello',
    yourconfig = 'anystring'
)

d.provide(instance)
```

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
python -m pinjected run my.module.print_hostname --hostname "{my.module2.load_hostname}"
```

This is useful for switching complicated injected instances for running the target. The complicated injected instances
can be trained ML models, etc.

Example2:

```python
# some.llm.module.py
from pinjected import injected


@injected
def llm_openai(openai_api_key, /, prompt):
    return "call open ai api with prompt..."


@injected
def llm_azure(azure_api_key, /, prompt):
    return "call azure api with prompt..."


@injected
def llm_llama(llama_model_on_gpu, configs, /, prompt):
    return llama_model_on_gpu(prompt, configs)


@injected
def chat(llm, /, prompt):
    return llm(prompt)
```

```bash
python -m pinjected run some.llm.module.chat --llm="{some.llm.module.llm_openai}" "hello!"
```

Now we can switch llm with llm_openai, llm_azure, llm_llama... by specifying a importable variable path.

## Dependency Configuration

`pinjected run` reads dependency configurations from two sources:

1. `__design__` variables in `__pinjected__.py` files (recommended)
2. `__meta_design__` variables in module files (legacy, being deprecated)

### Using `__pinjected__.py` Files (Recommended)

The recommended approach is to place `__pinjected__.py` files in your package directories:

```
- some_package
  | __init__.py
  | __pinjected__.py   [-- contains __design__
  | module1
  | | __init__.py
  | | __pinjected__.py [-- contains __design__
  | | util.py
```

When running "python -m pinjected run some_package.module1.util.run", all `__design__` variables from `__pinjected__.py` files in parent packages will be loaded and concatenated.

```python
# Example __pinjected__.py file
from pinjected import design

__design__ = design(
    config_key="config_value",
    another_key="another_value"
)
```

### Legacy `__meta_design__` Approach (Deprecated)

The older approach using `__meta_design__` variables in module files is being deprecated:

```
- some_package
  | __init__.py   [-- can contain __meta_design__
  | module1
  | | __init__.py [-- can contain __meta_design__
  | | util.py     [-- can contain __meta_design__
```

When running with this approach, all `__meta_design__` variables in parent packages will be loaded and concatenated:

```python
meta_design = some_package.__meta_design__ + some_package.module1.__meta_design + some_package.module1.util.__meta_design__
overrides = meta_design.provide('overrides')
default_design = import_if_exist(meta_design['default_design_path'])
g = (default_design + overrides).to_graph()
g[some_package.module1.util.run]
```

It's recommended to migrate to the new `__design__` in `__pinjected__.py` files approach.


## .pinjected.py

Additionaly, we can place .pinjected.py file in the current directly or the home directory. a global variable named '
default_design' and 'overrides' will be automatically imported, then prepended and appended to the design before running
the target.

This is convinient for specifying user specific injection variables such as api keys, or some user specific functions.

