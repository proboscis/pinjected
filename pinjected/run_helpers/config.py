import sys
from dataclasses import dataclass
from pathlib import Path

from returns.maybe import Some, maybe

from pinjected import Injected, design
from pinjected.helper_structure import MetaContext
from pinjected.helpers import find_default_design_paths
from pinjected.module_inspector import get_project_root
from pinjected.pinjected_logging import logger


@dataclass
class ConfigCreationArgs:
    module_path: str
    default_design_path: str = None
    runner_script_path: str = None
    interpreter_path: str = None
    working_dir: str = None

    def to_design(self):
        logger.debug(f"python paths:{sys.path}")
        meta_context = MetaContext.gather_from_path(Path(self.module_path))

        design_obj = (
            design(
                project_root=Injected.bind(
                    lambda module_path: Path(get_project_root(module_path))
                ),
                runner_script_path=Injected.bind(
                    lambda: self.runner_script_path or __file__
                ),
                interpreter_path=Injected.bind(
                    lambda: self.interpreter_path or sys.executable
                ),
                default_design_paths=Injected.bind(
                    lambda: find_default_design_paths(
                        self.module_path, self.default_design_path
                    )
                ),
                default_working_dir=Injected.bind(
                    lambda project_root: maybe(lambda: self.working_dir)()
                    | Some(str(project_root))
                ),
                default_design_path=Injected.bind(
                    lambda default_design_paths: default_design_paths[0]
                ),
                logger=logger,
                custom_idea_config_creator=Injected.bind(
                    lambda x: []
                ),  # type ConfigCreator
                meta_context=meta_context,
                module_path=self.module_path,
            )
            + meta_context.accumulated
        )
        logger.info(f"using meta design:{meta_context.accumulated}")
        logger.info(
            f"custom_idea_config_creator:{design_obj['custom_idea_config_creator']}"
        )
        return design_obj
