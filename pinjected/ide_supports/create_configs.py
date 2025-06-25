import asyncio
import inspect
import json
import os
import sys
from collections import defaultdict
from collections.abc import Callable, Mapping
from dataclasses import asdict
from pathlib import Path

from beartype import beartype
from returns.maybe import Maybe, Some
from returns.result import Success, safe

import pinjected
import pinjected.global_configs
from pinjected import Design, Designed, Injected, design, injected, instance
from pinjected.di.injected import InjectedFromFunction, PartialInjectedFunction
from pinjected.di.proxiable import DelegatedVar
from pinjected.di.metadata.location_data import ModuleVarLocation
from pinjected.graph_inspection import DIGraphHelper
from pinjected.helper_structure import (
    IdeaRunConfiguration,
    IdeaRunConfigurations,
    MetaContext,
)
from pinjected.module_inspector import ModuleVarSpec
from pinjected.module_var_path import ModuleVarPath
from pinjected.pinjected_logging import logger

__design__ = design(
    meta_config_value="from_design",
    # Additional configurations
    additional_config_value="only_in_design",
)

from pinjected.run_helpers.run_injected import run_injected
from pinjected.v2.keys import IBindKey


def run_with_meta_context(
    var_path: str,
    context_module_file_path: str,
    design_path: str | None = None,
    # TODO add overrides_path
    **kwargs,
):
    """
    This is for running a injected with __design__ integrated.

    IMPORTANT: This function is primarily used by IDE plugins and will use
    pinjected_internal_design by default if no design_path is provided.

    TODO: Deprecate meta_main entry point in favor of direct pinjected commands.

    :param var_path:
    :param context_module_file_path:
    :param design_path: Optional design path. If None, uses pinjected_internal_design
    :param kwargs:
    :return:
    """
    # if not "__meta_design__" in Path(context_module_file_path).read_text():
    #     raise ValueError(f"{context_module_file_path} does not contain __meta_design__")
    meta_context: MetaContext = asyncio.run(
        MetaContext.a_gather_bindings_with_legacy(Path(context_module_file_path))
    )

    # Use pinjected_internal_design by default if no design_path is provided
    # This is needed because IDE plugins (PyCharm, VSCode) don't pass design_path
    if design_path is None:
        logger.warning(
            "No design_path provided to run_with_meta_context. "
            "Using pinjected_internal_design by default. "
            "This behavior is for backward compatibility with IDE plugins."
        )
        design_path = "pinjected.ide_supports.default_design.pinjected_internal_design"

    default = design(default_design_paths=[])
    instance_overrides = design(
        module_path=Path(context_module_file_path),
        interpreter_path=sys.executable,
        meta_context=meta_context,
        **kwargs,
    )
    return run_injected(
        "get",
        var_path,
        design_path,
        return_result=True,
        overrides=default + meta_context.final_design + instance_overrides,
        notifier=logger.info,
    )


@instance
def __pinjected__wrap_output_with_tag():
    """
    A flag to control whether the output should be wrapped with <pinjected>...</pinjected> tags.
    This is used to differentiate pinjected output from other outputs in the same stdout stream.
    """
    return True


@instance
@beartype
def create_idea_configurations(
    inspect_and_make_configurations,
    module_path: Path,
    print_to_stdout,
    __pinjected__wrap_output_with_tag,
):
    with logger.contextualize(tag="create_idea_configurations"):
        pinjected.global_configs.pinjected_TRACK_ORIGIN = False
        configs: IdeaRunConfigurations = inspect_and_make_configurations(module_path)
        pinjected.global_configs.pinjected_TRACK_ORIGIN = True
        # logger.info(f"configs:{configs}")

        # since stdout is contaminated by many other modules,
        # We need to think of other way to pass information.
        # should I use a tempfile?
        # or, maybe we can use a separator... like <pinjected>...</pinjected>
        # so that the caller must parse the output.

        if print_to_stdout:
            data_str = json.dumps(asdict(configs))
            if __pinjected__wrap_output_with_tag:
                data_str = f"<pinjected>{data_str}</pinjected>"
            print(data_str)
        else:
            return configs


@instance
def list_injected_keys(default_design_paths: list[str]):
    helper = DIGraphHelper(ModuleVarPath(default_design_paths[0]).load())
    data_str = json.dumps(sorted(list(helper.total_mappings().keys())))
    print(data_str)


def get_filtered_signature(func):
    # Get the original signature
    original_signature = inspect.signature(func)

    # Filter out positional-only parameters
    filtered_params = {
        name: param
        for name, param in original_signature.parameters.items()
        if param.kind != inspect.Parameter.POSITIONAL_ONLY
    }

    # Create a new signature with the filtered parameters
    new_signature = original_signature.replace(parameters=filtered_params.values())

    # Convert the new signature to a string
    new_signature_str = str(new_signature)
    return func.__name__, new_signature_str


@instance
def list_completions(default_design_paths: list[str]):
    """
    An API to be called from IDE to return completions, based on __design__.
    :param default_design_paths:
    :return:[
        {name,description,tail}
    ]
    """
    if not default_design_paths:
        dat_str = f"<pinjected>{json.dumps([])}</pinjected>"
        print(dat_str)
        return
    helper = DIGraphHelper(ModuleVarPath(default_design_paths[0]).load())
    total_mappings: Mapping[str, Injected] = helper.total_mappings()
    logger.info(f"total_mappings:{total_mappings}")

    def key_to_completion(key):
        tgt = total_mappings[key]
        match tgt:
            case PartialInjectedFunction(
                InjectedFromFunction(object(__original__=func), _)
            ):
                name, signature = get_filtered_signature(func)
                return dict(name=name, description="injected function", tail=signature)

        return dict(
            name=key,
            description=f"injected {key}",  # the type text
            tail=f"",  # a function signature
        )

    # so, I want to extract the return type, and the function signature.
    # for this, we can utilize the llm.
    # the bindings are mostly PartialInjectedFunction and its proxy.

    completions = [key_to_completion(key) for key in helper.total_mappings()]
    data_str = json.dumps(completions)
    data_str = "<pinjected>" + data_str + "</pinjected>"
    print(data_str)


@instance
def design_metadata(default_design_paths: list[str]):
    d: Design = ModuleVarPath(default_design_paths[0]).load()
    # we load design, so we need to be careful with not to running things...
    """
    protocol->
    meta:{
        key:str
        location: str
    }
    location:{
        type: (path | coordinates)
        value: qualified_name | file_path:line_no:col_no
    }
    structure = list[meta]
    """
    helper = DIGraphHelper(d)
    metas = []
    for k, bind in helper.total_bindings().items():
        k: IBindKey
        match bind.metadata.bind(lambda m: m.code_location):
            case Some(ModuleVarPath(qualified_name)):
                metas.append(
                    dict(
                        key=k.ide_hint_string(),
                        location=dict(type="path", value=qualified_name),
                    )
                )
            case Some(ModuleVarLocation(fp, line, col)):
                metas.append(
                    dict(
                        key=k.ide_hint_string(),
                        location=dict(type="coordinates", value=f"{fp}:{line}:{col}"),
                    )
                )
    logger.info(f"metas:{metas}")
    data_str = json.dumps(metas)
    data_str = "<pinjected>" + data_str + "</pinjected>"
    print(data_str)


# TODO implement a provider of documentations
# TODO implement a provider for jump to definition, s that I can click on the injected variables to see the definition.
# TODO automatically add the injected variable key to the argument list when the user selects to use it.
# TODO show a list of injectable variables in the side bar, or the structure view
# TODO detect a variable assign ment from 'injected' functions and any calls that involve DelegatedVar or injected functions
# TODO make a PartialInjectedAsyncFunction and a proxy for it.


# Type alias for IDE configuration creators
IdeaConfigCreator = Callable[[ModuleVarSpec], list[IdeaRunConfiguration]]


@injected
def extract_args_for_runnable(logger, /, tgt: ModuleVarSpec, ddp: str, meta: dict):  # noqa: C901, PLR0912
    args = None
    match tgt.var, meta:
        case (_, Success({"kind": "callable"})):
            args = ["call", tgt.var_path, ddp]
        case (_, Success({"kind": "object"})):
            args = ["run", tgt.var_path, ddp]
        case (PartialInjectedFunction(), _):
            args = ["call", tgt.var_path, ddp]
        case (InjectedFromFunction(), _):
            args = ["call", tgt.var_path, ddp]
        case (Injected(), _):
            args = ["run", tgt.var_path, ddp]
        case (DelegatedVar(), _):
            # This handles both @instance decorated functions and IProxy
            args = ["run", tgt.var_path, ddp]
        case (Designed(), _):
            args = ["run", tgt.var_path, ddp]
        case _:
            args = None
    if args is not None:
        logger.info(f"args for {tgt.var_path} is {args}")
    else:
        logger.warning(f"could not extract args for {tgt.var_path}, {tgt.var}")
    return args


@injected
def injected_to_idea_configs(  # noqa: C901, PLR0912, PLR0915
    runner_script_path: str,
    interpreter_path: str,
    default_design_paths: list[str],
    default_working_dir: Maybe[str],
    extract_args_for_runnable,
    logger,
    internal_idea_config_creator: IdeaConfigCreator,
    custom_idea_config_creator: IdeaConfigCreator,
    /,
    tgt: ModuleVarSpec,
):
    """
    Creates IDE run configurations for injected targets.

    NOTE: This function currently relies on __runnable_metadata__ which is deprecated.
    Functions decorated with @instance don't automatically get this metadata anymore,
    so they won't appear in IDE configurations unless they explicitly have __runnable_metadata__.

    TODO: Update to use a new metadata system that works with @instance decorators.
    See: https://github.com/proboscis/pinjected/issues/93
    """
    from pinjected import __main__

    # question is: how can we pass the override to run_injected?
    logger.info(
        f"using custom_idea_config_creator {custom_idea_config_creator} for {tgt}"
    )
    name = tgt.var_path.split(".")[-1]
    # runner_script_path corresponds to the script's path which gets passed to idea.
    # so it must be the path which has run_injected command
    # Ensure runner_script_path is a string, not a function
    if callable(runner_script_path):
        runner_script_path = runner_script_path()

    config_args = {
        "script_path": runner_script_path,
        "interpreter_path": interpreter_path,
        "working_dir": default_working_dir.value_or(os.getcwd()),
    }

    assert isinstance(tgt, ModuleVarSpec)
    meta = safe(getattr)(tgt.var, "__runnable_metadata__")
    # so we need to gather the possible design paths from the metadata too.
    ddps = []
    match meta:
        case Success({"default_design_path": ddp}):
            ddps.append(ddp)
    ddps += default_design_paths
    results = defaultdict(list)

    if not ddps:
        logger.warning(
            f"no default design path provided for {tgt.var_path}, using pinjected.EmptyDesign"
        )
        ddps.append("pinjected.EmptyDesign")

    for ddp in ddps:
        args = extract_args_for_runnable(tgt, ddp, meta)
        # this, viz_branch should not be created by this function, but an injected function.
        if args is not None:
            ddp_name = ddp.split(".")[-1]
            config = dict(
                script_path=__main__.__file__,
                interpreter_path=interpreter_path,
                working_dir=default_working_dir.value_or(os.getcwd()),
                arguments=["run"] + args[1:],
                name=f"{name}({ddp_name})",
            )
            viz_config = dict(
                **config_args,
                arguments=["run_injected", "visualize"] + args[1:],
                name=f"{name}({ddp_name})_viz",
            )
            describe_config = {
                "script_path": __main__.__file__,
                "interpreter_path": interpreter_path,
                "working_dir": default_working_dir.value_or(os.getcwd()),
                "arguments": ["describe"] + args[1:],
                "name": f"describe {name}",
            }
            results[name].append(IdeaRunConfiguration(**config))
            results[name].append(IdeaRunConfiguration(**viz_config))
            results[name].append(IdeaRunConfiguration(**describe_config))
        else:
            # NOTE: __runnable_metadata__ is deprecated. @instance decorated functions
            # don't automatically get this metadata anymore, which is why they're skipped.
            # TODO: Update to use new metadata system
            logger.warning(
                f"skipping {tgt.var_path} because it has no __runnable_metadata__"
            )
    try:
        cfgs = custom_idea_config_creator(tgt)
        assert cfgs is not None, (
            f"custom_idea_config_creator {custom_idea_config_creator} returned None for {tgt}. return [] if you have no custom configs."
        )
        for configs in cfgs:
            results[name].append(configs)
    except Exception as e:
        logger.warning(f"Failed to create custom idea configs for {tgt} because {e}")
        raise RuntimeError(
            f"Failed to create custom idea configs for {tgt} because {e}"
        ) from e
    try:
        cfgs = internal_idea_config_creator(tgt)
        assert cfgs is not None, (
            f"internal_idea_config_creator {internal_idea_config_creator} returned None for {tgt}. return [] if you have no internal configs."
        )
        for configs in cfgs:
            results[name].append(configs)
    except Exception as e:
        logger.warning(f"Failed to create internal idea configs for {tgt} because {e}")
        raise RuntimeError(
            f"Failed to create internal idea configs for {tgt} because {e}"
        ) from e
    return IdeaRunConfigurations(configs=results)
