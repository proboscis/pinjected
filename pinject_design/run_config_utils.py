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
import asyncio
import importlib
import importlib.util
import json
import os
import sys
from copy import copy
from dataclasses import dataclass
from datetime import datetime
from pprint import pformat
from typing import Optional, List, Dict, Awaitable, Coroutine, Union

import loguru
import returns.maybe as raybe
from IPython import embed
from expression import Nothing
from pydantic import BaseModel, validator
from returns.maybe import Maybe, Some, maybe
from returns.result import safe, Success, Failure

import pinject_design.global_configs
from pinject_design import Injected, Design, Designed
from pinject_design.di.app_injected import InjectedEvalContext
from pinject_design.global_configs import PINJECT_DESIGN_TRACK_ORIGIN
from pinject_design.di.injected import injected_function
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


class RunnableValue(BaseModel):
    """
    I think it is easier to make as much configuration as possible on this side.
    """
    src: ModuleVarSpec[Union[Injected, Designed]]
    design_path: str

    @validator('src')
    def validate_src_type(cls, value):
        match value:
            case ModuleVarSpec(Injected(), _):
                return value
            case ModuleVarSpec(Designed(), _):
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
    configs: Dict[str, List[IdeaRunConfiguration]]


safe_getattr = safe(getattr)


def get_runnables(module_path) -> List[ModuleVarSpec]:
    def accept(name, tgt):
        match (name, tgt):
            case (n, _) if n.startswith("provide"):
                return True
            case (_, Injected()):
                return True
            case (_, Designed()):
                return True
            case (_, DelegatedVar(value, cxt)) if cxt == InjectedEvalContext:
                return True
            case (_, DelegatedVar(value, cxt)):
                return False
            case (_, item) if hasattr(item, "__runnable_metadata__") and isinstance(item.__runnable_metadata__, dict):
                return True
            case _:
                return False

    runnables = inspect_module_for_type(module_path, accept)
    return runnables


@injected_function
def extract_runnables(
        default_design_path,
        logger,
        /,
        injecteds: List[ModuleVarSpec[Injected]]
):
    def extract_runnable(i: ModuleVarSpec[Injected], meta):
        match i.var, meta, default_design_path:
            case (_, Success({"default_design_path": ddp}), _):
                return RunnableValue(src=i, design_path=ddp)
            case (_, Success(), Some(ddp)):
                return RunnableValue(src=i, design_path=ddp)
            case (_, Failure(), Some(ddp)) if callable(i.var):
                return RunnableValue(src=i, design_path=ddp)
            case (DelegatedVar(), _, Some(ddp)):
                return RunnableValue(src=i, design_path=ddp)
            case (_, Failure(), Some(ddp)):
                raise ValueError(f"Cannot find default design path for {i.var_path}")
            case (_, Maybe.empty):
                raise ValueError(f"Cannot find default design path for {i.var_path}")
            case _:
                raise NotImplementedError(
                    f"Unsupported case {i, meta, default_design_path}. make sure to provide default design path.")

    results = []
    for i in injecteds:
        if isinstance(i, ModuleVarSpec):
            meta = safe(getattr)(i.var, "__runnable_metadata__")
            results.append(safe(extract_runnable)(i, meta))
    failures = [r for r in results if isinstance(r, Failure)]
    logger.warning(f"Failed to extract runnable from {failures}")
    return [r.unwrap() for r in results if isinstance(r, Success)]


@injected_function
def inspect_and_make_configurations(
        entrypoint_path: str,
        interpreter_path: str,
        default_design_paths: List[str],
        default_working_dir: Maybe[str],
        logger,
        /,
        module_path
) -> IdeaRunConfigurations:
    assert isinstance(default_design_paths, list)
    runnables = get_runnables(module_path)
    logger.info(f"Found {len(runnables)} injecteds. {pformat(runnables)}")
    results = dict()
    safe_getattr = safe(getattr)
    for i in runnables:
        name = i.var_path.split(".")[-1]
        results[name] = []
        config_args = {
            'script_path': entrypoint_path,
            'interpreter_path': interpreter_path,
            'working_dir': default_working_dir.value_or(os.getcwd())
        }
        assert isinstance(i, ModuleVarSpec)
        meta = safe_getattr(i.var, "__runnable_metadata__")
        # so we need to gather the possible design paths
        ddps = []
        match meta:
            case Success({"default_design_path": ddp}):
                ddps.append(ddp)
        ddps += default_design_paths

        # for each ddp we create a run config named with design's name
        for ddp in ddps:
            args = None
            match i.var, meta:
                case (_, Success({"kind": "callable"})):
                    args = ['call', i.var_path, ddp]
                case (_, Success({"kind": "object"})):
                    args = ['get', i.var_path, ddp]
                case (_, Failure()) if callable(i.var):
                    args = ['get', i.var_path, ddp]
                case (Injected(), Failure()):
                    args = ['get', i.var_path, ddp]
                    logger.warning(f"using get for {i.var_path} because it has no __runnable_metadata__")
                case (DelegatedVar(), _):
                    args = ['get', i.var_path, ddp]
                    logger.warning(f"using get for {i.var_path} because it has no __runnable_metadata__")
                case (_, Failure()):
                    logger.info(f"skipping {i.var_path} because it has no __runnable_metadata__")
                case (_, Maybe.empty):
                    logger.info(f"skipping {i.var_path} because it has no default design path.")
                case (_, Success(_meta)) if "kind" not in meta:
                    args = ['get', i.var_path, ddp]
                case _:
                    raise NotImplementedError(
                        f"Unsupported case {i, meta, ddp}. make sure to provide default design path.")
            if args is not None:
                ddp_name = ddp.split(".")[-1]
                config = dict(
                    **config_args,
                    arguments=['run_injected'] + args,
                    name=f"{name}({ddp_name})"
                )
                viz_config = dict(
                    **config_args,
                    arguments=['run_injected', 'visualize'] + args[1:],
                    name=f"{name}({ddp_name})_viz",
                )
                results[name].append(IdeaRunConfiguration(**config))
                results[name].append(IdeaRunConfiguration(**viz_config))
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


notification_sounds = [
    "Basso",
    "Blow",
    "Bottle",
    "Frog",
    "Funk",
    "Glass",
    "Hero",
    "Morse",
    "Ping",
    "Pop",
    "Purr",
    "Sosumi",
    "Submarine",
    "Tink"
]


def notify(text, sound='Glass') -> str:
    """
    pops up a notification with text
    :param text:
    :return: Notification result
    """
    from loguru import logger
    import os
    org = text
    text = text.replace('"', '\\"')
    text = text.replace("'", "")
    script = f"'display notification \"{text}\" with title \"OpenAI notification\" sound name \"{sound}\"'"
    cmd = f"""osascript -e {script} """
    os.system(cmd)
    return f"Notified user with text: {org}"

# maybe we want to distinguish the error with its complexity and pass it to gpt if required.

def run_anything(cmd: str, var_path, design_path):
    # TODO pass the resulting errors into gpt to give better error messages.
    # for that, I need to capture the stderr/stdout
    # get the var and design
    # then run it based on cmd with args/kwargs
    from loguru import logger
    loaded_var = load_variable_by_module_path(var_path)
    meta = safe(getattr)(loaded_var, "__runnable_metadata__").value_or({})
    if not isinstance(meta, dict):
        meta = {}
    overrides = meta.get("overrides", instances())
    var: Injected = Injected.ensure_injected(load_variable_by_module_path(var_path))
    design: Design = load_variable_by_module_path(design_path)
    design = design + overrides
    # if you return python object, fire will try to use it as a command object
    # we need to inspect __runnable_metadata__
    logger.info(f"running target:{var}")
    logger.info(f"metadata obtained from injected: {meta}")
    res = None
    try:
        if cmd == 'call':
            res = design.provide(var)()
            if isinstance(res, Coroutine):
                res = asyncio.run(res)
            logger.info(f"run_injected result:\n{res}")
        elif cmd == 'get':
            res = design.provide(var)
            if isinstance(res, Coroutine):
                res = asyncio.run(res)
            logger.info(f"run_injected result:\n{res}")
        elif cmd == 'fire':
            res = design.provide(var)
            if isinstance(res, Coroutine):
                res = asyncio.run(res)
            logger.info(f"run_injected result:\n{res}")
        elif cmd == 'visualize':
            from loguru import logger
            logger.info(f"visualizing {var_path} with design {design_path}")
            logger.info(f"deps:{var.dependencies()}")
            design.to_vis_graph().show_injected_html(var)
    except Exception as e:
        notify(f"Run failed with error:\n{e}", sound='Frog')
        raise e
    notify(f"Run result:\n{res}")


@dataclass
class RunInjected:
    var_path: str
    design_path: str = None

    def __post_init__(self):
        if self.design_path is None:
            self.design_path = get_design_path_from_var_path(self.var_path)

    def _var_design(self):
        var: Injected = Injected.ensure_injected(load_variable_by_module_path(self.var_path))
        design: Design = load_variable_by_module_path(self.design_path)
        return var, design

    def _get(self):
        var, design = self._var_design()
        return design.provide(var)

    def chain_call(self, *args, **kwargs):
        res = self._get()(*args, **kwargs)
        if isinstance(res, Coroutine):
            res = asyncio.run(res)
        return res

    def chain_get(self):
        res = self._get()
        if isinstance(res, Coroutine):
            res = asyncio.run(res)
        return res

    def get(self):
        from loguru import logger
        logger.info(f"injected get result\n{self.chain_get()}")

    def call(self, *args, **kwargs):
        from loguru import logger
        logger.info(f"injected get result\n{self.chain_call(*args, **kwargs)}")

    def visualize(self):
        from loguru import logger
        logger.info(f"visualizing {self.var_path} with design {self.design_path}")
        var, design = self._var_design()
        design.to_vis_graph().show_injected_html(var)


def run_injected(
        cmd,
        var_path,
        design_path: str = None,
        *args, **kwargs
):
    from loguru import logger
    if design_path is None:
        design_path = get_design_path_from_var_path(var_path)
    assert design_path, f"design path must be a valid module path, got:{design_path}"
    return run_anything(cmd, var_path, design_path, *args, **kwargs)


def get_design_path_from_var_path(var_path):
    from loguru import logger
    logger.info(f"looking for default design paths from {var_path}")
    module_path = ".".join(var_path.split(".")[:-1])
    # we need to get the file path from var path
    logger.info(f"loading module:{module_path}")
    # Import the module
    module = importlib.import_module(module_path)
    module_path = module.__file__
    design_paths = find_default_design_paths(module_path, None)
    assert design_paths
    design_path = design_paths[0]
    return design_path


def run_with_kotlin(module_path: str, kotlin_zmq_address: str = None):
    d = instances()
    if kotlin_zmq_address is not None:
        d += instances(
            kotlin_zmq_address=kotlin_zmq_address
        )
    tgt: Injected = load_variable_by_module_path(module_path)
    g = d.to_graph()
    return g[tgt]


def send_kotlin_code(address: str, code: str):
    import zmq
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect(address)
    socket.send_string(code)
    response = socket.recv_string()
    return response


def find_default_design_path(file_path: str) -> Optional[str]:
    return find_module_attr(file_path, '__default_design_path__')


def find_default_working_dir(file_path: str) -> Optional[str]:
    return find_module_attr(file_path, '__default_working_dir__')


def find_module_attr(file_path: str, attr_name: str) -> Optional[str]:
    from loguru import logger
    logger.info(f"checking {file_path} for {attr_name}")
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


def find_injecteds(
        module_path
):
    injecteds = get_runnables(module_path)
    return print(json.dumps([i.var_path for i in injecteds]))


def find_default_design_paths(module_path, default_design_path):
    """
    :param module_path: absolute file path.("/")
    :param default_design_path: absolute module path (".")
    :return:
    """
    default_design_paths: list[str] = maybe(find_module_attr)(module_path, '__default_design_paths__').value_or([])
    default_design_path: list[str] = (
            maybe(lambda: default_design_path)() | maybe(find_default_design_path)(module_path)).map(
        lambda p: [p]).value_or([])
    default_design_paths = default_design_paths + default_design_path
    return default_design_paths


def create_configurations(
        module_path,
        default_design_path=None,
        entrypoint_path=None,
        interpreter_path=None,
        working_dir=None
):
    from loguru import logger
    import sys
    pinject_design.global_configs.PINJECT_DESIGN_TRACK_ORIGIN = False
    logger.debug(f"python paths:{sys.path}")
    # logger.debug(f"env python_path:{os.environ['PYTHONPATH']}")
    entrypoint_path = entrypoint_path or __file__
    interpreter_path = interpreter_path or sys.executable
    logger.info(f"looking for default design paths from {module_path}")
    default_design_paths = find_default_design_paths(module_path, default_design_path)
    default_working_dir = maybe(lambda: working_dir)() | maybe(get_project_root)(module_path)

    # somehow find the default design
    # for example by looking at a config file in the project root
    # 1. look for default design path string
    # 2. look for default working dir string

    design = instances(
        entrypoint_path=entrypoint_path,
        interpreter_path=interpreter_path,
        default_design_paths=default_design_paths,
        default_working_dir=default_working_dir,
        logger=loguru.logger
    )
    g = design.to_graph()
    configs: IdeaRunConfigurations = g[inspect_and_make_configurations](module_path)
    pinject_design.global_configs.PINJECT_DESIGN_TRACK_ORIGIN = True
    print(configs.json())


SANDBOX_TEMPLATE = """
from {design_path} import {design_name}
from {var_path} import {var_name}
g = {design_name}.to_graph()
tgt = g[{var_name}]
"""


@maybe
def retrieve_design_path_from_injected(tgt: Injected):
    meta = safe(getattr)(tgt, '__runnable_metadata__')
    match meta:
        case {"default_design_path": design_path}:
            return design_path


def make_sandbox(module_file_path, var_name):
    tgts = get_runnables(module_file_path)
    name_to_tgt = {tgt.var_path.split(".")[-1]: tgt for tgt in tgts}
    tgt: ModuleVarSpec = name_to_tgt[var_name]
    default_design_paths = find_default_design_paths(module_file_path, None)
    default_design_path = default_design_paths[0]
    default_design_path_parent = ".".join(default_design_path.split('.')[:-1])
    var_path_parent = ".".join(tgt.var_path.split('.')[:-1])
    # let's make a file for sandbox,
    # format datetime like 20230101_010101
    datetime_str_as_name = datetime.now().strftime("%Y%m%d_%H%M%S")
    sandbox_name = f"{var_name}_sandbox_{datetime_str_as_name}.py"
    sandbox_path = os.path.join(os.path.dirname(module_file_path), sandbox_name)
    with open(sandbox_path, 'w') as f:
        f.write(SANDBOX_TEMPLATE.format(
            design_path=default_design_path_parent,
            design_name=default_design_path.split('.')[-1],
            var_path=var_path_parent,
            var_name=var_name
        ))
    print(sandbox_path)


def main():
    import fire
    fire.Fire({
        'create_configurations': create_configurations,
        'run_injected': run_injected,
        'run_injected2': RunInjected,
        'run_with_kotlin': run_with_kotlin,
        'find_injecteds': find_injecteds,
        'make_sandbox': make_sandbox,
    })


if __name__ == '__main__':
    main()
