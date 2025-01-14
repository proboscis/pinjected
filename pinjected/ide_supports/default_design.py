from pathlib import Path

import loguru
from returns.maybe import Some

import pinjected.run_config_utils
from pinjected import instances, providers, Design
from pinjected.exporter.llm_exporter import add_export_config
from pinjected.helpers import inspect_and_make_configurations, find_default_design_paths
from pinjected.module_inspector import get_project_root
from pinjected.run_config_utils import injected_to_idea_configs
# This design is used for ide supports
pinjected_internal_design:Design = instances(
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
    internal_idea_config_creator=add_export_config,
)
