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
import inspect
import json
import os
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from pprint import pformat
from typing import Optional, List, Dict, Coroutine, OrderedDict, Callable

from loguru import logger
import fire
import loguru
import returns.maybe as raybe
from cytoolz import memoize
from expression import Nothing
from returns.maybe import Maybe, Some, maybe
from returns.result import safe, Success, Failure

import pinject_design.global_configs
from pinject_design import Injected, Design
from pinject_design.di.injected import injected_function
from pinject_design.di.proxiable import DelegatedVar
from pinject_design.di.util import instances, providers
from pinject_design.helper_structure import IdeaRunConfigurations, RunnablePair, RunnableValue, \
    IdeaRunConfiguration
from pinject_design.helpers import inspect_and_make_configurations, load_variable_by_module_path, \
    get_design_path_from_var_path, get_runnables, find_default_design_paths, gather_meta_context
from pinject_design.module_inspector import ModuleVarSpec, inspect_module_for_type, get_project_root
from pinject_design.run_config_utils_v2 import RunInjected
from dataclasses import dataclass


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

safe_getattr = safe(getattr)


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
    # question is: how can we pass the override to run_injected?
    logger.info(f"using custom_idea_config_creator {custom_idea_config_creator} for {tgt}")
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

def run_anything(cmd: str, var_path, design_path, return_result=False, *args, **kwargs):
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
    logger.info(f"running target:{var} with cmd {cmd}, args {args}, kwargs {kwargs}")
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
    if return_result:
        return res


def run_injected(
        cmd,
        var_path,
        design_path: str = None,
        return_result=False,
        *args, **kwargs
):
    if design_path is None:
        design_path = get_design_path_from_var_path(var_path)
    assert design_path, f"design path must be a valid module path, got:{design_path}"
    return run_anything(cmd, var_path, design_path,return_result=return_result, *args, **kwargs)


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


def find_injecteds(
        module_path
):
    injecteds = get_runnables(module_path)
    return print(json.dumps([i.var_path for i in injecteds]))


@dataclass
class ConfigCreationArgs:
    module_path: str
    default_design_path: str = None
    entrypoint_path: str = None
    interpreter_path: str = None
    working_dir: str = None

    def to_design(self):
        logger.debug(f"python paths:{sys.path}")
        meta_context = gather_meta_context(Path(self.module_path))

        design = providers(
            project_root=lambda: Path(get_project_root(self.module_path)),
            entrypoint_path=lambda: self.entrypoint_path or __file__,
            interpreter_path=lambda: self.interpreter_path or sys.executable,
            default_design_paths=lambda: find_default_design_paths(self.module_path, self.default_design_path),
            default_working_dir=lambda project_root: maybe(lambda: self.working_dir)() | Some(
                str(project_root)),
            default_design_path=lambda default_design_paths: default_design_paths[0]
        ) + instances(
            logger=loguru.logger,
            custom_idea_config_creator=lambda x: [],  # type ConfigCreator
            meta_context=meta_context,
        ) + meta_context.accumulated
        logger.info(f"using meta design:{meta_context.accumulated}")
        logger.info(f"custom_idea_config_creator:{design['custom_idea_config_creator']}")
        return design


# since this is an entrypoint, we can't use @injected_function here.
def create_idea_configurations(
        module_path,
        default_design_path=None,
        entrypoint_path=None,
        interpreter_path=None,
        working_dir=None,
        print_to_stdout=True,
):
    pinject_design.global_configs.PINJECT_DESIGN_TRACK_ORIGIN = False
    args = ConfigCreationArgs(
        module_path=module_path,
        default_design_path=default_design_path,
        entrypoint_path=entrypoint_path,
        interpreter_path=interpreter_path,
        working_dir=working_dir,
    )
    design = args.to_design()
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


def get_var_spec_from_module_path_and_name(module_path: str, var_name: str) -> ModuleVarSpec:
    tgts = get_runnables(module_path)
    name_to_tgt = {tgt.var_path.split(".")[-1]: tgt for tgt in tgts}
    tgt: ModuleVarSpec = name_to_tgt[var_name]
    return tgt


@injected_function
def _make_sandbox_impl(
        default_design_path: str,
        /,
        module_file_path: str,
        var_name: str,
):
    tgt: ModuleVarSpec = get_var_spec_from_module_path_and_name(module_file_path, var_name)
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


def make_sandbox(module_file_path, var_name):
    args = ConfigCreationArgs(
        module_path=module_file_path,
        default_design_path=None,
        entrypoint_path=None,
        interpreter_path=None,
        working_dir=None,
    )
    design = args.to_design()
    g = design.to_graph()
    return g[_make_sandbox_impl](module_file_path=module_file_path, var_name=var_name)


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
    if isinstance(query, dict):
        return instances(**query)
    elif query is None:
        return Design()
    elif query.endswith('.json'):
        import json
        if not Path(query).exists():
            raise ValueError(f"cannot find {query} for configuration.")
        return instances(**json.load(open(query)))
    elif query.endswith('.yaml'):
        import yaml
        if not Path(query).exists():
            raise ValueError(f"cannot find {query} for configuration.")
        return instances(**yaml.load(open(query), Loader=yaml.SafeLoader))
    else:
        try:
            import json
            return instances(**json.loads(query))
        except:
            raise ValueError(f"cannot parse {query} as json")


def load_variable_from_script(script_file: Path, varname: str):
    spec = importlib.util.spec_from_file_location("module.name", script_file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, varname)


def parse_override_path(p) -> Design:
    if "::" in p:
        file, varname = p.split("::")
        return load_variable_by_module_path(Path(file), varname)
    else:
        load_variable_by_module_path(p)


def run_main():
    """
    inspect the caller's frame for runnable target and design path.
    delegates its execution to fire.Fire.

    I want to resolve the override, but we don't know which protocol we should use.

    get the file this is run,
    find the runnables
    find the designs
    pass it to fire.

    The protocol to override design:
    1. python file
    - /path/to/config.py::design_name
    2. python module path
    - my.package.design_name
    3. yaml or json file
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
        return lambda *args, **kwargs: run_idea_conf(conf, *args, **kwargs)

    return fire.Fire({
        k: make_enetrypoint(conf[0]) for k, conf in confs.configs.items()
    })


def run_idea_conf(conf: IdeaRunConfiguration, *args, **kwargs):
    pre_args = conf.arguments[1:]
    return run_injected(*pre_args,return_result=True, *args, **kwargs)


@memoize
def get_designs_from_module(module_path: Path):
    from loguru import logger
    logger.info(f"trying to import designs from {module_path}")

    def accept(name, x):
        return isinstance(x, Design) and name != "__meta_design__"

    return inspect_module_for_type(module_path, accept)


@injected_function
def get_designs_from_meta_var(
        var_path_to_file_path,
        /,
        meta: ModuleVarSpec
) -> List[ModuleVarSpec]:
    return get_designs_from_module(var_path_to_file_path(meta.var_path))


@injected_function
def var_path_to_file_path(project_root: Path, /, var_path: str) -> Path:
    module_path = '.'.join(var_path.split(".")[:-1])
    return Path(str(project_root / module_path.replace(".", os.path.sep)) + ".py")


if __name__ == '__main__':
    main()
