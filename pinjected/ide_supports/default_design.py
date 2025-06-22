from pathlib import Path

from returns.maybe import Some

from pinjected import Design, Injected, design
from pinjected.exporter.llm_exporter import add_export_config
from pinjected.helpers import find_default_design_paths, inspect_and_make_configurations
from pinjected.module_inspector import get_project_root
from pinjected.pinjected_logging import logger
from pinjected.ide_supports.create_configs import injected_to_idea_configs

# This design is used for ide supports
pinjected_internal_design: Design = design(
    logger=logger,
    runner_script_path=Injected.pure(lambda: __import__("pinjected").__main__.__file__),
    custom_idea_config_creator=Injected.pure(lambda spec: []),  # type ConfigCreator
    # this becomes recursive and overflows if we call meta_session inside a parent design...
    default_design_path=None,
    print_to_stdout=True,
    inspect_and_make_configurations=inspect_and_make_configurations,
    injected_to_idea_configs=injected_to_idea_configs,
    default_design_paths=Injected.bind(
        lambda module_path, default_design_path: find_default_design_paths(
            module_path, default_design_path
        )
    ),
    project_root=Injected.bind(lambda module_path: Path(get_project_root(module_path))),
    default_working_dir=Injected.bind(lambda project_root: Some(str(project_root))),
    internal_idea_config_creator=add_export_config,
)
