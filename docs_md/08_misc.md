
# Visualization (Supported after 0.1.128)
Pinjected supports visualization of dependency graph.
```bash
pinjected run_injected visualize <full.path.of.Injected.variable> <full.path.of.Design.variable>
```
For example:
```bash
pinjected run_injected visualize pinjected.test_package.child.module1.test_viz_target pinjected.test_package.child.module1.viz_target_design
```

# Picklability
Compatible with dill and cloudpickle as long as the bound objects are picklable.


# IDE-support
A plugin exists for IntelliJ Idea to run Injected variables directly from the IDE.

Requirements:
- IntelliJ Idea
- Dependency configuration using either:
  - `__design__` variable in a `__pinjected__.py` file (recommended)
  - `__meta_design__` variable in a python file (legacy, being deprecated)

### 1. Install the plugin to IntelliJ Idea/PyCharm
### 2. open a python file.
Write a pinjected script, for example:
```python
# test_package/test.py
from pinjected import Injected, injected, instance
from returns.maybe import Some, Nothing


@instance
async def test_variable():
  """
  this test_vaariable can now directly be run from IntelliJ Idea, by clicking the Run button associated with this line.
  a green triangle will appear on the left side of the function definition.
  """
  return 1
```

Then create a `__pinjected__.py` file in the same directory:
```python
# test_package/__pinjected__.py
from pinjected import design
from returns.maybe import Some, Nothing

__design__ = design(
    default_design_path='test_package.design',
    default_working_dir=Some("/home/user/test_repo"), # use Some() to override, and Nothing to infer from the project structure.
)
```

The legacy approach using `__meta_design__` in module files is being deprecated:
```python
# test_package/test.py (legacy approach - not recommended)
from pinjected import design, Injected, injected, instance
from returns.maybe import Some, Nothing


@instance
async def test_variable():
  return 1

__meta_design__ = design(
    default_design_path='test_package.design',
    default_working_dir=Some("/home/user/test_repo"),
)
```

Now, you can run the `test_variable` by clicking the green triangle on the left side of the function definition.

## Customizing the Injected variable run
To add additional run configurations to appear on the Run button, you can add bindings to your dependency configuration.

The recommended approach is to use `__design__` in a `__pinjected__.py` file:

```python
# __pinjected__.py
from pinjected import design
from typing import List, Callable

CustomIdeaConfigCreator = Callable[[ModuleVarSpec], List[IdeaRunConfiguration]]


@injected
def add_custom_run_configurations(
        interpreter_path:str,
        default_working_dir,
        /,
        cxt: ModuleVarSpec) -> List[IdeaRunConfiguration]:
    return [IdeaRunConfiguration(
        name="HelloWorld",
        script_path="~/test_repo/test_script.py",
        interpreter_path=interpreter_path,# or your specific python's path, "/usr/bin/python3",
        arguments=["--hello", "world"],
        working_dir="~/test_repo", # you can use default_working_dir
    )]

__design__ = design(
    custom_idea_config_creator=add_custom_run_configurations
)
```

The legacy approach using `__meta_design__` in module files is being deprecated:

```python
# module.py (legacy approach - not recommended)
from pinjected import design
from typing import List, Callable

CustomIdeaConfigCreator = Callable[[ModuleVarSpec], List[IdeaRunConfiguration]]


@injected
def add_custom_run_configurations(
        interpreter_path:str,
        default_working_dir,
        /,
        cxt: ModuleVarSpec) -> List[IdeaRunConfiguration]:
    return [IdeaRunConfiguration(
        name="HelloWorld",
        script_path="~/test_repo/test_script.py",
        interpreter_path=interpreter_path,
        arguments=["--hello", "world"],
        working_dir="~/test_repo",
    )]

__meta_design__ = design(
    custom_idea_config_creator=add_custom_run_configurations
)
```

You can use interpreter_path and default_working_dir  as dependencies, which are automatically injected by the plugin.
Other dependencies are resolved using __meta_design__ accumulated from all parent packages. You can use this to inject anything you need during the run configuration creation.

Here is an example of submitting an injected variable to a ray cluster as a job:
```python


@dataclass
class RayJobSubmitter:
  _a_run_ray_job: Callable[..., Awaitable[None]]
  job_kwargs: dict
  runtime_env: dict
  preparation: Callable[[], Awaitable[None]]
  override_design_path: ModuleVarPath = field(default=None)
  additional_entrypoint_args: List[str] = field(default_factory=list)
  #here you can set --xyz=123 to override values

  async def submit(self, tgt):
    await self.preparation()
    entrypoint = f"python -m pinjected run {tgt}"
    if self.override_design_path:
      entrypoint += f" --overrides={self.override_design_path.path}"
    if self.additional_entrypoint_args:
      entrypoint += " " + " ".join(self.additional_entrypoint_args)
    await self._a_run_ray_job(
      entrypoint=entrypoint,
      runtime_env=self.runtime_env,
      **self.job_kwargs
    )


@injected
def add_submit_job_to_ray(
        interpreter_path,
        default_working_dir,
        default_design_paths: List[str],
        __resolver__: AsyncResolver,
        /,
        tgt: ModuleVarSpec,
) -> List[IdeaRunConfiguration]:
    """
    We need to be able to do the following:
    :param interpreter_path:
    :param default_working_dir:
    :param default_design_paths:
    :param ray_runtime_env:
    :param ray_client:
    :param tgt:
    :return:
    """
    # Example command:
    # python  -m pinjected run sge_seg.a_cmd_run_ray_job
    # --ray_client={ray_cluster_manager.gpuaas_ray_cluster_manager.gpuaas_job_port_forward}
    # --ray-job-entrypoint="echo hello"
    # --ray-job-kwargs=""
    # --ray-job-runtime-env=""
    try:
        submitter:RayJobSubmitter = __resolver__.to_blocking()['ray_job_submitter_path']
        # here we use dynamic resolution, since some scripts don't have ray_job_submitter_path in __meta_design__
    except Exception as e:
        logger.warning(f"Failed to resolve ray_job_submitter_path: {e}")
        raise e
        return []

    """
    options to pass secret variables:
    1. set it here as a --ray-job-kwargs
    2. use env var
    3. upload ~/.pinjected.py <- most flexible, but need a source .pinject.py file  
    
    """
    tgt_script_path = ModuleVarPath(tgt.var_path).module_file_path

    conf = IdeaRunConfiguration(
        name=f"submit_ray({tgt.var_path.split('.')[-1]})",
        script_path=str(pinjected.__file__).replace("__init__.py", "__main__.py"),
        interpreter_path=interpreter_path,
        arguments=[
            "run",
            "ray_cluster_manager.intellij_ray_job_submission.a_cmd_run_ray_job",
            f"{default_design_paths[0]}",
            f"--meta-context-path={tgt_script_path}",
            f"--ray-job-submitter={{{submitter}}}",
            f"--ray-job-tgt={tgt.var_path}",

        ],
        working_dir=default_working_dir.value_or("."),
    )

    return [conf]


```

