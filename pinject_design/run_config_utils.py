"""
I need to define a generic structure for the followings:
- 1. Injected Function without default design
- 2. Injected Function like thing with default design
- Injected Function like thing with default design and a artifact identifier to be used as an artifact <= this can actually just be simplified as 2.

# what about the default args?
# actually, the variables canbe Injected[T] and Injected[Callable]
# but there is no way to tell that unless you actually running them.
so there are several combinations
1. Injected
2. Injected[Callable]
3. Injected with Deisgn
4. Injected[Callable] with Design

# and we need to distinguish Injected and Injected[Callable]
so, let's assume that the instance is Injected at default
and ask user to mark Injected[Callable] in the python side with annotation.
To do so we need to make Injected have some metadata... but it's not reliable.
But we can use isinstance for tagging it.
Alright.. but how do we give the optional design?
Hmm, an easy way is to add some metadata though..
Adding feature to an existing data structure is not recommended.
So I guess I need to introduce a new data structure.
"""
import os
import importlib
import importlib.util
import sys
from copy import copy
from pprint import pformat
from typing import Optional, List

import loguru
from expression import Nothing
from pydantic import BaseModel, validator
import returns.maybe as raybe
from returns.maybe import Maybe, Some, maybe
from returns.result import safe, Success, Result, Failure

from pinject_design import Injected, Design
from pinject_design.di.app_injected import InjectedEvalContext
from pinject_design.di.injected import InjectedWithDefaultDesign, InjectedFunction, injected_function
from pinject_design.di.proxiable import DelegatedVar
from pinject_design.di.util import instances
from pinject_design.module_inspector import ModuleVarSpec, inspect_module_for_type, get_project_root


def maybe__or__(self, other):
    match self:
        case Some(x):
            return self
        case raybe.Nothing:
            return other


def maybe_filter(self: Maybe, flag_to_keep):
    match self.map(flag_to_keep):
        case Some(True):
            return self
        case _:
            return Nothing


Maybe.__or__ = maybe__or__
Maybe.filter = maybe_filter


class RunnableInjected(BaseModel):
    """
    I think it is easier to make as much configuration as possible on this side.
    """
    src: ModuleVarSpec[Injected]
    design: Optional[ModuleVarSpec[Design]]

    @validator('src')
    def validate_src_type(cls, value):
        match value:
            case ModuleVarSpec(Injected(), _):
                return value
            case _:
                raise ValueError(f"src must be an instance of Injected of ModuleVarSpec, but got {value}")

    class Config:
        arbitrary_types_allowed = True


class IdeaRunConfiguration(BaseModel):
    name: str
    script_path: str
    interpreter_path: str
    arguments: List[str]
    working_dir: str
    # we need dependency python librarrie's paths.
    # this needs to be checked from intellij side


class IdeaRunConfigurations(BaseModel):
    configs: List[IdeaRunConfiguration]


@injected_function
def inspect_and_make_configurations(
        entrypoint_path: str,
        interpreter_path: str,
        default_design_path: Maybe[str],
        default_working_dir: Maybe[str],
        logger,
        /,
        module_path
) -> IdeaRunConfigurations:
    def accept(name, tgt):
        if name.startswith("provide_"):
            return True
        elif isinstance(tgt, Injected):
            return True
        elif isinstance(tgt, DelegatedVar):
            if tgt.cxt == InjectedEvalContext:
                return True

    injecteds = inspect_module_for_type(module_path, accept)
    logger.info(f"Found {len(injecteds)} injecteds. {pformat(injecteds)}")
    results = []
    for i in injecteds:
        config_args = {
            'name': i.var_path.split(".")[-1],
            'script_path': entrypoint_path,
            'interpreter_path': interpreter_path,
            'working_dir': default_working_dir.value_or(os.getcwd())
        }
        args = None
        # TODO InjectedFunctions are not guaranteed to return a function
        # So let's rely on __runnable_metadata__
        if isinstance(i, ModuleVarSpec):
            meta = safe(getattr)(i.var,"__runnable_metadata__")
            # hmm, it is too hard to tell whether the object should be told or not.
            # I guess we just return 'get' for all of them. and
            # let 'run_injected' to decide whether to call it or not...?
            # Or we can mark the callable ones with some metadata.
            # Injected[Function] as IFunc = Injected[Function]
            # or let user select from the popup?
            match i.var,meta, default_design_path:
                case (_,Success({"kind":"callable","default_design_path":ddp}),_):
                    args = ['call', i.var_path, ddp]
                case (_,Success({"kind":"callable"}),Some(ddp)):
                    args = ['call', i.var_path, ddp]
                case (_,Success({"kind":"object","default_design_path":ddp}),_):
                    args = ['get', i.var_path, ddp]
                case (_,Success({"kind":"object"}),Some(ddp)):
                    args = ['get', i.var_path, ddp]
                case (_,Failure(), Some(ddp)) if callable(i.var):
                    args = ['get', i.var_path, ddp]
                case (Injected(),Failure(), Some(ddp)):
                    args = ['get', i.var_path, ddp]
                    logger.warning(f"using get for {i.var_path} because it has no __runnable_metadata__")
                case (DelegatedVar(),_, Some(ddp)):
                    args = ['get', i.var_path, ddp]
                    logger.warning(f"using get for {i.var_path} because it has no __runnable_metadata__")
                case (_,Failure(), Some(ddp)):
                    logger.info(f"skipping {i.var_path} because it has no __runnable_metadata__")
                case (_, Maybe.empty):
                    logger.info(f"skipping {i.var_path} because it has no default design path.")
                case _:
                    raise NotImplementedError(
                        f"Unsupported case {i,meta, default_design_path}. make sure to provide default design path.")
        if args is not None:
            run_args = ['run_injected'] + args
            viz_args = ['run_injected', 'visualize'] + args[1:]
            results.append(IdeaRunConfiguration(**config_args, arguments=run_args))
            viz_configs = copy(config_args)
            viz_configs['name'] = f"{viz_configs['name']}_viz"
            results.append(IdeaRunConfiguration(**viz_configs, arguments=viz_args))
    return IdeaRunConfigurations(configs=results)


def load_variable_by_module_path(full_module_path):
    module_path_parts = full_module_path.split('.')
    variable_name = module_path_parts[-1]
    module_path = '.'.join(module_path_parts[:-1])

    # Import the module
    module = importlib.import_module(module_path)

    # Retrieve the variable using getattr()
    variable = getattr(module, variable_name)

    return variable


def run_injected(cmd: str, var_path, design_path, *args, **kwargs):
    # get the var and design
    # then run it based on cmd with args/kwargs
    from loguru import logger
    var: Injected = Injected.ensure_injected(load_variable_by_module_path(var_path))
    design: Design = load_variable_by_module_path(design_path)
    # if you return python object, fire will try to use it as a command object
    if cmd == 'call':
        res = design.provide(var)(*args, **kwargs)
        logger.info(f"run_injected result:\n{res}")
    elif cmd == 'get':
        res = design.provide(var)
        logger.info(f"run_injected result:\n{res}")
    elif cmd == 'visualize':
        from loguru import logger
        logger.info(f"visualizing {var_path} with design {design_path}")
        design.to_vis_graph().show_injected_html(var)
    elif cmd == "sandbox":
       # TODO make a ~sandbox.py file and edit it?
        pass




def find_default_design_path(file_path: str) -> Optional[str]:
    return find_module_attr(file_path, '__default_design_path__')


def find_default_working_dir(file_path: str) -> Optional[str]:
    return find_module_attr(file_path, '__default_working_dir__')


def find_module_attr(file_path: str, attr_name: str) -> Optional[str]:
    from loguru import logger
    root_module_path = get_project_root(file_path)
    if not file_path.startswith(root_module_path):
        return None

    relative_path = os.path.relpath(file_path, root_module_path)
    module_name = os.path.splitext(relative_path.replace(os.sep, '.'))[0]
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    logger.info(f"importing {module_name}")
    sys.modules[module_name] = module
    spec.loader.exec_module(module)

    if hasattr(module, attr_name):
        return getattr(module, attr_name)

    parent_dir = os.path.dirname(file_path)
    if parent_dir != root_module_path:
        parent_file_path = os.path.join(parent_dir, '__init__.py')
        if os.path.exists(parent_file_path) and parent_file_path != file_path:
            return find_module_attr(parent_file_path, attr_name)
        else:
            grandparent_dir = os.path.dirname(parent_dir)
            grandparent_file_path = os.path.join(grandparent_dir, '__init__.py')
            if os.path.exists(grandparent_file_path):
                return find_module_attr(grandparent_file_path, attr_name)

    return None


def create_configurations(
        module_path,
        default_design_path=None,
        entrypoint_path=None,
        interpreter_path=None,
        working_dir=None
):
    from loguru import logger
    import sys
    import os
    logger.debug(f"python paths:{sys.path}")
    #logger.debug(f"env python_path:{os.environ['PYTHONPATH']}")
    entrypoint_path = entrypoint_path or __file__
    interpreter_path = interpreter_path or sys.executable
    default_design_path = maybe(lambda: default_design_path)() | maybe(find_default_design_path)(module_path)
    default_working_dir = maybe(lambda: working_dir)() | maybe(get_project_root)(module_path)

    # somehow find the default design
    # for example by looking at a config file in the project root
    # 1. look for default design path string
    # 2. look for default working dir string

    design = instances(
        entrypoint_path=entrypoint_path,
        interpreter_path=interpreter_path,
        default_design_path=default_design_path,
        default_working_dir=default_working_dir,
        logger=loguru.logger
    )
    g = design.to_graph()
    configs: IdeaRunConfigurations = g[inspect_and_make_configurations](module_path)
    print(configs.json())


def main():
    import fire
    fire.Fire({
        'create_configurations': create_configurations,
        'run_injected': run_injected,
    })


if __name__ == '__main__':
    main()
