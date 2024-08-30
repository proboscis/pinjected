import importlib
from dataclasses import dataclass, field
from pathlib import Path

from beartype import beartype
from returns.maybe import maybe
from typing import Optional

from pinjected import injected_function
from pinjected.helper_structure import IdeaRunConfigurations
from pinjected.maybe_patch import patch_maybe
from pinjected.module_helper import walk_module_attr
from pinjected.module_inspector import ModuleVarSpec
from pinjected.module_var_path import ModuleVarPath
from pinjected.runnables import get_runnables

patch_maybe()

@injected_function
@beartype
def inspect_and_make_configurations(
        injected_to_idea_configs,
        logger,
        /,
        module_path:Path
) -> IdeaRunConfigurations:
    runnables = get_runnables(module_path)
    logger.info(f"Found {len(runnables)} injecteds")
    results = dict()
    logger.info(f"found {len(runnables)} injecteds")
    for tgt in runnables:
        if isinstance(tgt, ModuleVarSpec):
            results.update(injected_to_idea_configs(tgt).configs)
    return IdeaRunConfigurations(configs=results)


@dataclass
class RunnableSpec:
    tgt_path: ModuleVarPath
    design_path: ModuleVarPath = field(default_factory=lambda: ModuleVarPath("pinjected.di.util.EmptyDesign"))

    def __post_init__(self):
        # add type check
        assert isinstance(self.tgt_path, ModuleVarPath)
        assert isinstance(self.design_path, ModuleVarPath)

    @property
    def target_name(self):
        return self.tgt_path.var_name

    @property
    def design_name(self):
        return self.design_path.var_name


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
    #assert design_paths, f"no default design paths found for {var_path}"
    if design_paths:
        design_path = design_paths[0]
        return design_path


def find_default_design_path(file_path: str) -> Optional[str]:
    from loguru import logger
    logger.info(f"looking for default design_path")
    return find_module_attr(file_path, '__default_design_path__')


def find_default_working_dir(file_path: str) -> Optional[str]:
    from loguru import logger
    logger.info(f"looking for default working dir")
    return find_module_attr(file_path, '__default_working_dir__')


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


def find_module_attr(file_path: str, attr_name: str, root_module_path: str = None) -> Optional[str]:
    for item in walk_module_attr(Path(file_path), attr_name, root_module_path):
        return item.var


