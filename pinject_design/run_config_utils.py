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
import inspect
import json
import os
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from pprint import pformat
from typing import Optional, List, Dict, Coroutine, Union, OrderedDict, Callable

import fire
import loguru
import returns.maybe as raybe
from cytoolz import memoize
from expression import Nothing
from pydantic import BaseModel, validator
from returns.maybe import Maybe, Some, maybe
from returns.result import safe, Success, Failure

import pinject_design.global_configs
from pinject_design import Injected, Design, Designed, EmptyDesign
from pinject_design.di.app_injected import InjectedEvalContext
from pinject_design.di.injected import injected_function
from pinject_design.di.proxiable import DelegatedVar
from pinject_design.di.util import instances, providers
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
def extract_args_for_runnable(
        logger,
        /,
        tgt: ModuleVarSpec,
        ddp: str,
        meta: dict
):
    args = None
    match tgt.var, meta:
        case (_, Success({"kind": "callable"})):
            args = ['call', tgt.var_path, ddp]
        case (_, Success({"kind": "object"})):
            args = ['get', tgt.var_path, ddp]
        case (_, Failure()) if callable(tgt.var):
            args = ['get', tgt.var_path, ddp]
        case (Injected(), Failure()):
            args = ['get', tgt.var_path, ddp]
            logger.warning(f"using get for {tgt.var_path} because it has no __runnable_metadata__")
        case (DelegatedVar(), _):
            args = ['get', tgt.var_path, ddp]
            logger.warning(f"using get for {tgt.var_path} because it has no __runnable_metadata__")
        case (_, Failure()):
            logger.info(f"skipping {tgt.var_path} because it has no __runnable_metadata__")
        case (_, Maybe.empty):
            logger.info(f"skipping {tgt.var_path} because it has no default design path.")
        case (_, Success(_meta)) if "kind" not in meta:
            args = ['get', tgt.var_path, ddp]
        case _:
            raise NotImplementedError(
                f"Unsupported case {tgt, meta, ddp}. make sure to provide default design path.")
    return args


IdeaConfigCreator = Callable[[ModuleVarSpec], List[IdeaRunConfiguration]]


@injected_function
def injected_to_idea_configs(
        entrypoint_path: str,
        interpreter_path: str,
        default_design_paths: List[str],
        default_working_dir: Maybe[str],
        extract_args_for_runnable,
        logger,
        custom_idea_config_creator: IdeaConfigCreator,
        /,
        tgt: ModuleVarSpec
):
    logger.info(f"using custom_idea_config_creator {custom_idea_config_creator}")
    name = tgt.var_path.split(".")[-1]
    config_args = {
        'script_path': entrypoint_path,
        'interpreter_path': interpreter_path,
        'working_dir': default_working_dir.value_or(os.getcwd())
    }
    assert isinstance(tgt, ModuleVarSpec)
    meta = safe_getattr(tgt.var, "__runnable_metadata__")
    # so we need to gather the possible design paths from the metadata too.
    ddps = []
    match meta:
        case Success({"default_design_path": ddp}):
            ddps.append(ddp)
    ddps += default_design_paths
    results = defaultdict(list)

    for ddp in ddps:
        args = extract_args_for_runnable(tgt, ddp, meta)
        # this, viz_branch should not be created by this function, but an injected function.
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
    try:
        for configs in custom_idea_config_creator(tgt):
            results[name].append(configs)
    except Exception as e:
        logger.warning(f"Failed to create custom idea configs for {tgt} because {e}")
        raise RuntimeError(f"Failed to create custom idea configs for {tgt} because {e}") from e
    return IdeaRunConfigurations(configs=results)


@injected_function
def inspect_and_make_configurations(
        injected_to_idea_configs,
        logger,
        /,
        module_path
) -> IdeaRunConfigurations:
    runnables = get_runnables(module_path)
    logger.info(f"Found {len(runnables)} injecteds")
    results = dict()
    logger.info(f"found {len(runnables)} injecteds")
    for tgt in runnables:
        if isinstance(tgt, ModuleVarSpec):
            results.update(injected_to_idea_configs(tgt).configs)
    return IdeaRunConfigurations(configs=results)


def load_variable_by_module_path(full_module_path):
    from loguru import logger
    logger.info(f"loading {full_module_path}")
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
    import os
    org = text
    text = text.replace('"', '\\"')
    text = text.replace("'", "")
    script = f"'display notification \"{text}\" with title \"OpenAI notification\" sound name \"{sound}\"'"
    cmd = f"""osascript -e {script} """
    os.system(cmd)
    return f"Notified user with text: {org}"


# maybe we want to distinguish the error with its complexity and pass it to gpt if required.

def run_anything(cmd: str, var_path, design_path, *args, **kwargs):
    # TODO pass the resulting errors into gpt to give better error messages.
    # for that, I need to capture the stderr/stdout
    # get the var and design
    # then run it based on cmd with args/kwargs
    # TODO I need a way to hook the run configurations
    # 1. add hooks for create_configurations => let the create_configurations load hook_design.
    # - this can make it possible to return a design runner that submits the design to cluster / local / docker etc.
    # 2. add hooks for run_injected => let the run_injected us hook_design for running the Injected.
    #

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
            res = design.provide(var)(*args, **kwargs)
            if isinstance(res, Coroutine):
                res = asyncio.run(res)
            logger.info(f"run_injected call result:\n{res}")
        elif cmd == 'get':
            res = design.provide(var)
            if isinstance(res, Coroutine):
                res = asyncio.run(res)
            logger.info(f"run_injected get result:\n{pformat(res)}")
        elif cmd == 'fire':
            res = design.provide(var)
            if isinstance(res, Coroutine):
                res = asyncio.run(res)
            logger.info(f"run_injected fire result:\n{res}")
        elif cmd == 'visualize':
            from loguru import logger
            logger.info(f"visualizing {var_path} with design {design_path}")
            logger.info(f"deps:{var.dependencies()}")
            design.to_vis_graph().show_injected_html(var)
    except Exception as e:
        notify(f"Run failed with error:\n{e}", sound='Frog')
        raise e
    notify(f"Run result:\n{str(res)[:100]}")


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
    from loguru import logger
    logger.info(f"looking for default design_path")
    return find_module_attr(file_path, '__default_design_path__')


def find_default_working_dir(file_path: str) -> Optional[str]:
    from loguru import logger
    logger.info(f"looking for default working dir")
    return find_module_attr(file_path, '__default_working_dir__')


def find_module_attr(file_path: str, attr_name: str, root_module_path: str = None) -> Optional[str]:
    for item in walk_module_attr(Path(file_path), attr_name, root_module_path):
        return item.var


def walk_module_attr(file_path: Path, attr_name, root_module_path=None):
    """
    walk down from a root module to the file_path, while looking for the attr_name and yielding the found variable as ModuleVarSpec
    :param file_path:
    :param attr_name:
    :return:
    """
    from loguru import logger
    if root_module_path is None:
        root_module_path = Path(get_project_root(str(file_path)))
    if not str(file_path).startswith(str(root_module_path)):
        return

    relative_path = file_path.relative_to(root_module_path)
    module_name = os.path.splitext(str(relative_path).replace(os.sep, '.'))[0]
    if module_name not in sys.modules:
        logger.info(f"importing module: {module_name}")
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
    module = sys.modules[module_name]
    if hasattr(module, attr_name):
        yield ModuleVarSpec(
            var=getattr(module, attr_name),
            var_path=module_name + '.' + attr_name,
        )

    parent_dir = file_path.parent
    if parent_dir != root_module_path:
        parent_file_path = parent_dir / '__init__.py'
        if parent_file_path.exists() and parent_file_path != file_path:
            yield from walk_module_attr(parent_file_path, attr_name, root_module_path)
        else:
            grandparent_dir = parent_dir.parent
            grandparent_file_path = grandparent_dir / '__init__.py'
            if grandparent_file_path.exists():
                yield from walk_module_attr(grandparent_file_path, attr_name, root_module_path)


def gather_meta_design(file_path: Path, meta_design_name: str = "__meta_design__"):
    designs = list(walk_module_attr(file_path, meta_design_name))
    designs.reverse()
    res = Design()
    for item in designs:
        res = res + item.var
    return res


def find_injecteds(
        module_path
):
    injecteds = get_runnables(module_path)
    return print(json.dumps([i.var_path for i in injecteds]))


def find_default_design_paths(module_path, default_design_path: Optional[str]) -> list[str]:
    """
    :param module_path: absolute file path.("/")
    :param default_design_path: absolute module path (".")
    :return:
    """
    default_design_paths: list[str] = maybe(find_module_attr)(module_path, '__default_design_paths__').value_or([])
    default_design_path: list[str] = (
            maybe(lambda: default_design_path)() | maybe(find_default_design_path)(module_path)).map(
        lambda p: [p]).value_or([])
    from loguru import logger
    logger.debug(f"default design paths:{default_design_paths}")
    logger.debug(f"default design path:{default_design_path}")
    default_design_paths = default_design_paths + default_design_path
    return default_design_paths


def create_idea_configurations(
        module_path,
        default_design_path=None,
        entrypoint_path=None,
        interpreter_path=None,
        working_dir=None,
        print_to_stdout=True,
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
    meta_design = gather_meta_design(Path(module_path))

    design = instances(
        entrypoint_path=entrypoint_path,
        interpreter_path=interpreter_path,
        default_design_paths=default_design_paths,
        default_working_dir=default_working_dir,
        logger=loguru.logger,
        custom_idea_config_creator=lambda x: [],  # type ConfigCreator
    ) + meta_design
    logger.info(f"using meta design:{meta_design}")
    logger.info(f"custom_idea_config_creator:{design['custom_idea_config_creator']}")
    g = design.to_graph()
    configs: IdeaRunConfigurations = g[inspect_and_make_configurations(module_path)]
    pinject_design.global_configs.PINJECT_DESIGN_TRACK_ORIGIN = True
    if print_to_stdout:
        print(configs.json())
    else:
        return configs


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


def create_main_command(
        targets: OrderedDict[str, Injected],
        design_paths: OrderedDict[str, str],
):
    def main(target: str, design_path: Optional[str] = None):
        tgt = targets[target]
        if design_path is None:
            design_path = design_paths[list(design_paths.keys())[0]]
        design = load_variable_by_module_path(design_path)
        cmd = design.to_graph()[tgt]
        return cmd

    return main


@dataclass
class RunnablePair:
    target: Injected
    design: Design

    def run(self):
        return self.design.to_graph()[self.target]

    def save_html(self, name: str = None, show=True):
        if name is None:
            name = "graph.html"
        self.design.to_vis_graph().save_as_html(self.target, name, show=show)


@injected_function
def create_runnable_pair(
        main_targets: OrderedDict[str, Injected],
        main_design_paths: OrderedDict[str, str],
        main_override_resolver,
        /,
        target: str,
        design_path: Optional[str] = None,
        overrides: str = None,
        show_graph: bool = False
) -> Optional[RunnablePair]:
    """
    :param main_targets:
    :param main_design_paths:
    :param target:
    :param design_path:
    :param overrides:
    :return:
    """

    tgt = main_targets[target]
    if design_path is None:
        design_path = main_design_paths[list(main_design_paths.keys())[0]]
    main_overrides = main_override_resolver(overrides)
    design = load_variable_by_module_path(design_path) + main_overrides
    pair = RunnablePair(target=tgt, design=design)
    if show_graph:
        pair.save_html()
    else:
        return pair.run()
    # cmd = design.to_graph()[tgt]
    # return cmd


def provide_module_path(logger, root_frame):
    frame_info = inspect.getframeinfo(root_frame)
    module_path = frame_info.filename
    logger.debug(f"module path:{module_path}")
    return module_path


def provide_runnables(logger, module_path) -> Dict[str, Injected]:
    tgts = get_runnables(module_path)
    name_to_tgt = {tgt.var_path.split(".")[-1]: tgt.var for tgt in tgts}
    logger.info(f"main targets:{pformat(name_to_tgt.keys())}")
    return name_to_tgt


def provide_design_paths(logger, module_path) -> OrderedDict[str, str]:
    design_paths = find_default_design_paths(module_path, None)
    design_paths = {design_path.split('.')[-1]: design_path for design_path in design_paths}
    logger.info(f"main design paths:{pformat(design_paths.keys())}")
    return design_paths


@injected_function
def main_override_resolver(query) -> Design:
    """
    :param query: can be filename with .json, .yaml.
    we can also try parsing it as json.
    :return:
    """
    if query is None:
        return Design()
    elif query.endswith('.json'):
        import json
        return instances(**json.load(open(query)))
    elif query.endswith('.yaml'):
        import yaml
        return instances(**yaml.load(open(query), Loader=yaml.SafeLoader))
    else:
        try:
            import json
            return instances(**json.loads(query))
        except:
            raise ValueError(f"cannot parse {query} as json")


def run_main():
    """
    inspect the caller's frame for runnable target and design path.
    delegates its execution to fire.Fire.

    I want to resolve the override, but we don't know which protocol we should use.

    get the file this is run,
    find the runnables
    find the designs
    pass it to fire.
    :return:
    """
    import inspect
    import fire
    from loguru import logger
    runnable: RunnablePair = (instances(
        root_frame=inspect.currentframe().f_back,
        logger=logger,
    ) + providers(
        module_path=provide_module_path,
        main_targets=provide_runnables,
        main_design_paths=provide_design_paths
    )).provide(create_runnable_pair)
    fire.Fire(runnable)


def main():
    import fire
    fire.Fire({
        'create_configurations': create_idea_configurations,
        'run_injected': run_injected,
        'run_injected2': RunInjected,
        'run_with_kotlin': run_with_kotlin,
        'find_injecteds': find_injecteds,
        'make_sandbox': make_sandbox,
    })


def pinject_main():
    """
    finds any runnable in the caller's file
    and runs it with default design with fire
    :return:
    """
    import inspect
    caller_frame = inspect.stack()[1]
    caller_file = caller_frame.filename
    confs: IdeaRunConfigurations = create_idea_configurations(
        caller_file,
        print_to_stdout=False
    )

    def make_enetrypoint(conf):
        return lambda *args,**kwargs: run_idea_conf(conf,*args,**kwargs)

    return fire.Fire({
        k: make_enetrypoint(conf[0]) for k, conf in confs.configs.items()
    })


def run_idea_conf(conf: IdeaRunConfiguration,*args,**kwargs):
    pre_args = conf.arguments[1:]
    return run_injected(*pre_args,*args,**kwargs)


if __name__ == '__main__':
    main()
