# Config Creator for Intellij Idea

Through `__meta_design__`, a custom run config creator can be created for Intellij Idea. This is useful for running the
target with different injected instances.

We introduce a IRunner interface that can be used to run arbitrary shell command on a target.
For example, we can implement a runner for GCE, AWS, Local, or Docker.

```python
class IRunner:
    async def run(self, cmd: str) -> str:
        pass

# an example of a local runner:
class LocalRunner(IRunner):
    async def run(self, cmd: str) -> str:
        import subprocess
        return subprocess.run(cmd, shell=True, capture_output=True).stdout.decode()
```

We call this runner an environment, to run a command.

Now, we can use this env to automatically add a run configuration for an injected object to be run on the target
environment.

This means that we can run any `injected` object on chosen environment.

To do so, we need to add a config creator to your dependency configuration. The recommended approach is to use `__design__` in a `__pinjected__.py` file:

```python
# __pinjected__.py
from pinjected import design, idea_config_craetor_from_envs

__design__ = design(
    custom_idea_config_craetor=idea_config_craetor_from_envs(
        [
            "some_module.local_env"
        ]
    )
)
```

The legacy approach using `__meta_design__` in module files is being deprecated:

```python
# some_module.py (legacy approach - not recommended)
from pinjected import *

local_env = injected(LocalRunner)()

__meta_design__ = design(
    custom_idea_config_craetor=idea_config_craetor_from_envs(
        [
            "some_module.local_env"
        ]
    )
)
```

Now, with pinjected plugin installed on intellij or vscode, you can click on the green triangle on the left of an `injected`
variable,
and then select an environment `local_env` to run it.

By implementing IRunner for any environment of your choice,
You can quickly switch the target environment for running the injected object.

