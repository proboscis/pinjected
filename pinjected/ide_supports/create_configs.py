import inspect
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Mapping

from beartype import beartype
from loguru import logger
from returns.maybe import Some

import pinjected
import pinjected.global_configs
from pinjected import instances, Injected, Design, instance, injected
from pinjected.di.injected import PartialInjectedFunction, InjectedFromFunction
from pinjected.di.metadata.location_data import ModuleVarLocation
from pinjected.graph_inspection import DIGraphHelper
from pinjected.helper_structure import MetaContext, IdeaRunConfigurations
from pinjected.helpers import inspect_and_make_configurations
from pinjected.module_var_path import ModuleVarPath

__meta_design__ = instances(
    # ah, this makes my code load my_design
    default_design_paths=["pinjected.ide_supports.default_design.pinjected_internal_design"]
)

from pinjected.run_helpers.run_injected import run_injected
from pinjected.v2.keys import IBindKey


def run_with_meta_context(
        var_path: str,
        context_module_file_path: str,
        design_path: str = None,
        # TODO add overrides_path
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
    meta_context = MetaContext.gather_from_path(Path(context_module_file_path))
    default = instances(
        default_design_paths=[]
    )
    instance_overrides = instances(
        module_path=Path(context_module_file_path),
        interpreter_path=sys.executable,
        meta_context=meta_context,
    ) + instances(**kwargs)
    return run_injected("get", var_path, design_path, return_result=True,
                        overrides=default + meta_context.accumulated + instance_overrides,
                        notifier=logger.info
                        )


@injected
def load_meta_context(
        module_path
):
    meta_context = MetaContext.gather_from_path(module_path)
    return meta_context


@injected
@beartype
def create_idea_configurations(
        inspect_and_make_configurations,
        module_path: Path,
        print_to_stdout,
        /,
        wrap_output_with_tag=True
):
    pinjected.global_configs.pinjected_TRACK_ORIGIN = False
    configs: IdeaRunConfigurations = inspect_and_make_configurations(module_path)
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


@instance
def list_injected_keys(
        default_design_paths: list[str]
):
    helper = DIGraphHelper(ModuleVarPath(default_design_paths[0]).load())
    data_str = json.dumps(sorted(list(helper.total_mappings().keys())))
    print(data_str)


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


@instance
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
        dat_str = f"<pinjected>{json.dumps([])}</pinjected>"
        print(dat_str)
        return
    helper = DIGraphHelper(ModuleVarPath(default_design_paths[0]).load())
    total_mappings: Mapping[str, Injected] = helper.total_mappings()
    logger.info(f"total_mappings:{total_mappings}")

    def key_to_completion(key):
        tgt = total_mappings[key]
        match tgt:
            case PartialInjectedFunction(InjectedFromFunction(object(__original__=func), kw_mapping)):
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
    data_str = json.dumps(completions)
    data_str = "<pinjected>" + data_str + "</pinjected>"
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
        k: IBindKey
        match bind.metadata.bind(lambda m: m.code_location):
            case Some(ModuleVarPath(qualified_name)):
                metas.append(dict(
                    key=k.ide_hint_string(),
                    location=dict(
                        type="path",
                        value=qualified_name
                    )
                ))
            case Some(ModuleVarLocation(fp, line, col)):
                metas.append(dict(
                    key=k.ide_hint_string(),
                    location=dict(
                        type="coordinates",
                        value=f'{fp}:{line}:{col}'
                    )
                ))
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
