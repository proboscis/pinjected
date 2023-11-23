import inspect
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Mapping

import loguru
from loguru import logger
from returns.maybe import Some

import pinjected
import pinjected.global_configs
from pinjected import injected_function, instances, providers, injected_instance, Injected, Design, instance
from pinjected.di.injected import PartialInjectedFunction, InjectedFunction
from pinjected.di.metadata.location_data import ModuleVarLocation
from pinjected.graph_inspection import DIGraphHelper
from pinjected.helper_structure import MetaContext
from pinjected.helpers import inspect_and_make_configurations, find_default_design_paths
from pinjected.module_inspector import get_project_root
from pinjected.module_var_path import ModuleVarPath
from pinjected.run_config_utils import injected_to_idea_configs

__meta_design__ = instances(
    default_design_paths=["pinjected.ide_supports.create_configs.my_design"]
)

from pinjected.run_helpers.run_injected import run_injected


def run_with_meta_context(
        var_path: str,
        context_module_file_path: str,
        design_path: str = None,
        **kwargs
):
    """
    This is for running a injected with __meta_design__ integrated.
    :param var_path:
    :param context_module_file_path:
    :param design_path:
    :param kwargs:
    :return:
    """
    if not "__meta_design__" in Path(context_module_file_path).read_text():
        raise ValueError(f"{context_module_file_path} does not contain __meta_design__")
    meta_context = MetaContext.gather_from_path(context_module_file_path)
    instance_overrides = instances(
        module_path=context_module_file_path,
        interpreter_path=sys.executable,
        meta_context=meta_context
    ) + instances(**kwargs)
    return run_injected("get", var_path, design_path, return_result=True,
                        overrides=meta_context.accumulated + instance_overrides,
                        notifier=logger.info
                        )


@injected_function
def load_meta_context(
        module_path
):
    meta_context = MetaContext.gather_from_path(module_path)
    return meta_context


my_design = instances(
    logger=loguru.logger,
    runner_script_path=pinjected.run_config_utils.__file__,
    custom_idea_config_creator=lambda spec: [],  # type ConfigCreator
    # this becomes recursive and overflows if we call meta_session inside a parent design...
    default_design_path=None,
    print_to_stdout=True
) + providers(
    inspect_and_make_configurations=inspect_and_make_configurations,
    injected_to_idea_configs=injected_to_idea_configs,
    default_design_paths=lambda module_path, default_design_path: find_default_design_paths(module_path,
                                                                                            default_design_path),
    project_root=lambda module_path: Path(get_project_root(module_path)),
    default_working_dir=lambda project_root: Some(str(project_root)),
)


@injected_function
def create_idea_configurations(
        inspect_and_make_configurations,
        module_path,
        print_to_stdout,
        /,
        wrap_output_with_tag=True
):
    pinjected.global_configs.pinjected_TRACK_ORIGIN = False
    configs = inspect_and_make_configurations(module_path)
    pinjected.global_configs.pinjected_TRACK_ORIGIN = True
    logger.info(f"configs:{configs}")

    # since stdout is contaminated by many other modules,
    # We need to think of other way to pass information.
    # should I use a tempfile?
    # or, maybe we can use a separator... like <pinjected>...</pinjected>
    # so that the caller must parse the output.

    if print_to_stdout:
        data_str = (json.dumps(asdict(configs)))
        if wrap_output_with_tag:
            data_str = f"<pinjected>{data_str}</pinjected>"
        print(data_str)
    else:
        return configs


@injected_instance
def list_injected_keys(
        default_design_paths: list[str]
):
    helper = DIGraphHelper(ModuleVarPath(default_design_paths[0]).load())
    print(json.dumps(sorted(list(helper.total_mappings().keys()))))


def get_filtered_signature(func):
    # Get the original signature
    original_signature = inspect.signature(func)

    # Filter out positional-only parameters
    filtered_params = {
        name: param for name, param in original_signature.parameters.items() if
        param.kind != inspect.Parameter.POSITIONAL_ONLY
    }

    # Create a new signature with the filtered parameters
    new_signature = original_signature.replace(parameters=filtered_params.values())

    # Convert the new signature to a string
    new_signature_str = str(new_signature)
    return func.__name__, new_signature_str


@injected_instance
def list_completions(
        default_design_paths: list[str]
):
    """
    An API to be called from IDE to return completions, based on __meta_design__.
    :param default_design_paths:
    :return:[
        {name,description,tail}
    ]
    """
    if not default_design_paths:
        print(f"<pinjected>{json.dumps([])}</pinjected>")
        return
    helper = DIGraphHelper(ModuleVarPath(default_design_paths[0]).load())
    total_mappings: Mapping[str, Injected] = helper.total_mappings()
    logger.info(f"total_mappings:{total_mappings}")

    def key_to_completion(key):
        tgt = total_mappings[key]
        match tgt:
            case PartialInjectedFunction(InjectedFunction(object(__original__=func), kw_mapping)):
                name, signature = get_filtered_signature(func)
                return dict(
                    name=name,
                    description="injected function",
                    tail=signature
                )

        return dict(
            name=key,
            description=f"injected {key}",  # the type text
            tail=f""  # a function signature
        )

    # so, I want to extract the return type, and the function signature.
    # for this, we can utilize the llm.
    # the bindings are mostly PartialInjectedFunction and its proxy.

    completions = [key_to_completion(key) for key in helper.total_mappings().keys()]
    data_str=json.dumps(completions)
    data_str = "<pinjected>"+data_str+"</pinjected>"
    print(data_str)


@instance
def design_metadata(
        default_design_paths: list[str]
):
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
        match bind.metadata.bind(lambda m: m.code_location):
            case Some(ModuleVarPath(qualified_name)):
                metas.append(dict(
                    key=k,
                    location=dict(
                        type="path",
                        value=qualified_name
                    )
                ))
            case Some(ModuleVarLocation(fp, line, col)):
                metas.append(dict(
                    key=k,
                    location=dict(
                        type="coordinates",
                        value=f'{fp}:{line}:{col}'
                    )
                ))
    logger.info(f"metas:{metas}")
    print(json.dumps(metas))

# TODO implement a provider of documentations
# TODO implement a provider for jump to definition, s that I can click on the injected variables to see the definition.
# TODO automatically add the injected variable key to the argument list when the user selects to use it.
# TODO show a list of injectable variables in the side bar, or the structure view
# TODO detect a variable assign ment from 'injected' functions and any calls that involve DelegatedVar or injected functions
# TODO make a PartialInjectedAsyncFunction and a proxy for it.
