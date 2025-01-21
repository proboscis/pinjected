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
import importlib
import inspect
import json
import os
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from pprint import pformat
from typing import Optional, List, Dict, OrderedDict, Callable, Any

import loguru
from cytoolz import memoize
from loguru import logger
from returns.maybe import Maybe, Some, maybe
from returns.result import safe, Success, Failure

from pinjected import Injected, Design, injected_function, Designed
from pinjected.di.expr_util import Expr, Call, Object
from pinjected.di.injected import PartialInjectedFunction, InjectedFromFunction
from pinjected.di.proxiable import DelegatedVar
from pinjected.di.util import instances, providers
from pinjected.exporter.llm_exporter import add_export_config
# from pinjected.ide_supports.create_configs import create_idea_configurations
from pinjected.helper_structure import IdeaRunConfigurations, RunnablePair, IdeaRunConfiguration
from pinjected.helpers import find_default_design_paths
from pinjected.maybe_patch import patch_maybe
from pinjected.module_inspector import ModuleVarSpec, inspect_module_for_type
from pinjected.module_var_path import ModuleVarPath, load_variable_by_module_path
from pinjected.run_config_utils_v2 import RunInjected
from pinjected.run_helpers.config import ConfigCreationArgs
from pinjected.runnables import get_runnables, RunnableValue

safe_getattr = safe(getattr)

patch_maybe()


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
            logger.warning(f"using get for {tgt.var_path} (type Injected) because it has no __runnable_metadata__")
        case (Designed(),Failure()):
            args = ['get', tgt.var_path, ddp]
            logger.warning(f"using get for {tgt.var_path} (type Designed) because it has no __runnable_metadata__")
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
        runner_script_path: str,
        interpreter_path: str,
        default_design_paths: List[str],
        default_working_dir: Maybe[str],
        extract_args_for_runnable,
        logger,
        internal_idea_config_creator:IdeaConfigCreator,
        custom_idea_config_creator: IdeaConfigCreator,
        /,
        tgt: ModuleVarSpec
):
    # question is: how can we pass the override to run_injected?
    logger.info(f"using custom_idea_config_creator {custom_idea_config_creator} for {tgt}")
    name = tgt.var_path.split(".")[-1]
    # runner_script_path corresponds to the script's path which gets passed to idea.
    # so it must be the path which has run_injected command
    config_args = {
        'script_path': runner_script_path,
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

    if not ddps:
        logger.warning(f"no default design path provided for {tgt.var_path}, using pinjected.EmptyDesign")
        ddps.append('pinjected.EmptyDesign')

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
        else:
            logger.warning(f"skipping {tgt.var_path} because it has no __runnable_metadata__")
    try:
        cfgs = custom_idea_config_creator(tgt)
        assert cfgs is not None, f"custom_idea_config_creator {custom_idea_config_creator} returned None for {tgt}. return [] if you have no custom configs."
        for configs in cfgs:
            results[name].append(configs)
    except Exception as e:
        logger.warning(f"Failed to create custom idea configs for {tgt} because {e}")
        raise RuntimeError(f"Failed to create custom idea configs for {tgt} because {e}") from e
    try:
        cfgs = internal_idea_config_creator(tgt)
        assert cfgs is not None, f"internal_idea_config_creator {internal_idea_config_creator} returned None for {tgt}. return [] if you have no internal configs."
        for configs in cfgs:
            results[name].append(configs)
    except Exception as e:
        logger.warning(f"Failed to create internal idea configs for {tgt} because {e}")
        raise RuntimeError(f"Failed to create internal idea configs for {tgt} because {e}") from e
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


# maybe we want to distinguish the error with its complexity and pass it to gpt if required.


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


# since this is an entrypoint, we can't use @injected_function here.


default_design = design = providers(
    # project_root=lambda module_path: Path(get_project_root(module_path)),
    # runner_script_path=lambda: self.runner_script_path or __file__,
    # interpreter_path=lambda: self.interpreter_path or sys.executable,
    # default_design_paths=lambda: find_default_design_paths(self.module_path, self.default_design_path),
    # default_working_dir=lambda project_root: maybe(lambda: self.working_dir)() | Some(
    #    str(project_root)),
    # default_design_path=lambda default_design_paths: default_design_paths[0]
) + instances(
    logger=loguru.logger,
    custom_idea_config_creator=lambda x: [],  # type ConfigCreator
    # meta_context=meta_context,
    # module_path=self.module_path,
    #
)

SANDBOX_TEMPLATE = """
from {design_path} import {design_name}
from {var_path} import {var_name}
d = {design_name} 
g = d.to_graph()
{deps}
#%%
{extras}
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


def extract_extra_codes(ast: Expr) -> ModuleVarPath:
    # TODO include the module path in the Inejcted Function
    match ast:
        case Call(
            Object(InjectedFromFunction(object(__original_code__=code, __name__=name, __module__=mod), _args)),
            args,
            kwargs):
            mvp = ModuleVarPath(f"{mod}.{name}")
            return mvp
        case _:
            return None


@injected_function
def make_sandbox_extra(tgt: ModuleVarSpec):
    match tgt.var:
        case DelegatedVar():
            impl_mvp = extract_extra_codes(tgt.var.eval().ast)
            import_lines = []
            impl = ""
            if impl_mvp is not None:
                import_lines += impl_mvp.depending_import_lines()
                impl = impl_mvp.definition_snippet()

            mvp = ModuleVarPath(tgt.var_path)
            import_lines += mvp.depending_import_lines()
            import_lines = '\n'.join(import_lines)
            usage = mvp.definition_snippet()
            return f"""
{import_lines}
{impl}
{usage}
"""
        case PartialInjectedFunction(InjectedFromFunction(object(__original_code__=usage), args)):
            return f"""
{usage}
"""
        case _:
            return ""


@injected_function
def _make_sandbox_impl(
        default_design_path: str,
        make_sandbox_extra: Callable[[Any], str],
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
    sandbox_name = f"__sandbox__{var_name}_{datetime_str_as_name}.py"
    sandbox_path = os.path.join(os.path.dirname(module_file_path), sandbox_name)

    logger.info(f"inspecting {var_name} to make sandbox")
    injected: Injected = Injected.ensure_injected(tgt.var)
    dependencies = injected.dependencies()
    extras = make_sandbox_extra(tgt)

    with open(sandbox_path, 'w') as f:
        deps = ""
        for d in dependencies:
            deps += f"{d} = g['{d}']\n"

        f.write(SANDBOX_TEMPLATE.format(
            design_path=default_design_path_parent,
            design_name=default_design_path.split('.')[-1],
            var_path=var_path_parent,
            var_name=var_name,
            deps=deps,
            extras=extras,
        ))

    print(sandbox_path)


def make_sandbox(module_file_path, var_name):
    args = ConfigCreationArgs(
        module_path=module_file_path,
        default_design_path=None,
        runner_script_path=None,
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
        default_design_paths: List[str],
        main_override_resolver,
        /,
        target: str,
        design_path: Optional[str] = None,
        overrides: str = None,
        show_graph: bool = False
) -> Optional[RunnablePair]:
    logger.info(f"creating runnable pair with {target},{design_path},{overrides}")
    logger.info(f"main targets:{pformat(main_targets.keys())},{target}")
    tgt = main_targets[target]
    if design_path is None:
        design_path = default_design_paths[0]
    main_overrides = main_override_resolver(overrides)
    design = load_variable_by_module_path(design_path) + main_overrides
    assert isinstance(design, Design), f"design at {design_path} must be Design, but got {design}"
    logger.info(f"design:{design} at {design_path}")
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
    import json
    from returns.pipeline import is_successful
    if isinstance(query, dict):
        return instances(**query)
    elif query is None:
        return EmptyDesign
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
    elif is_successful(safe(json.loads)(query)):
        return instances(**json.loads(query))
    else:
        return ModuleVarPath(query).load()


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
    module_path = provide_module_path(logger, inspect.currentframe().f_back)
    cfg = ConfigCreationArgs(
        module_path=module_path,
    )
    # runnable: RunnablePair = (instances(
    #     root_frame=inspect.currentframe().f_back,
    #     logger=logger,
    # ) + providers(
    #     module_path=provide_module_path,
    #     main_targets=provide_runnables,
    #     main_design_paths=provide_design_paths
    # )).provide(create_runnable_pair)
    d = cfg.to_design() + instances(
        logger=logger,
    ) + providers(
        main_targets=provide_runnables,
    )
    runnable: RunnablePair = d.provide(create_runnable_pair)
    fire.Fire(runnable)


def main():
    import fire
    # maybe we should switch these commands by Injected, right?
    # we want each implementations to have design...
    # well, we can use python -m pinjected .... for these commands as well ,right?
    from pinjected.run_helpers.run_injected import run_injected
    fire.Fire({
        # 'create_configurations': create_idea_configurations,
        'run': run_injected,
        'run_injected': run_injected,
        'run_injected2': RunInjected,
        'run_with_kotlin': run_with_kotlin,
        'find_injecteds': find_injecteds,
        'make_sandbox': make_sandbox,
    })


def run_idea_conf(conf: IdeaRunConfiguration, *args, **kwargs):
    pre_args = conf.arguments[1:]
    from pinjected.run_helpers.run_injected import run_injected
    return run_injected(*pre_args, return_result=True, *args, **kwargs)


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

__meta_design__ = instances(
    default_design_paths=["pinjected.run_config_utils.__meta_design__"]
) + providers(
    internal_idea_config_creator=add_export_config
)
