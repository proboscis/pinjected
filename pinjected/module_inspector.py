import importlib.util
import os
import sys
from typing import List, Generic, TypeVar, Any, Callable, Union
from pathlib import Path

import fire
from cytoolz import memoize
from pydantic import BaseModel
from pydantic.dataclasses import dataclass

T = TypeVar("T")


@dataclass
class ModuleVarSpec(Generic[T]):
    var: T
    var_path: str

    @property
    def module_file_path(self):
        from pinjected.module_var_path import ModuleVarPath
        return ModuleVarPath(self.var_path).module_file_path


@memoize
def get_project_root(start_path: str) -> str:
    from loguru import logger
    current_path = os.path.dirname(os.path.abspath(start_path))
    #logger.debug(f"current_path:{current_path}")
    while os.path.exists(os.path.join(current_path, "__init__.py")):
        parent_path = os.path.dirname(current_path)
        if parent_path == current_path:
            raise ValueError("Project root not found")
        current_path = parent_path
        #logger.debug(f"current_path:{current_path}")
    # this handles the case where
    # /repos/repo_name/package/__init__.py
    # but not the case where
    # /repos/repo_name/src/package/__init__.py
    # how can we detect if src should be included?
    if (p_path := Path(current_path)).name == 'src':
        current_path = str(p_path.parent)
    return current_path


def get_module_path(root_path, module_path):
    relative_path = os.path.relpath(module_path, root_path)
    without_extension = os.path.splitext(relative_path)[0]
    return without_extension.replace(os.path.sep, ".")


def inspect_module_for_type(module_path: Union[str, Path], accept: Callable[[str, Any], bool]) -> List[
    ModuleVarSpec[T]]:
    if isinstance(module_path, Path):
        module_path = str(module_path)
    from loguru import logger
    project_root = get_project_root(os.path.dirname(module_path))
    logger.info(f"project_root:{project_root}")
    module_name = get_module_path(project_root, module_path)
    logger.info(f"module_name:{module_name}")
    if module_name not in sys.modules:
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        # Register the module in sys.modules
        sys.modules[module_name] = module
    module = sys.modules[module_name]
    # Iterate through the module's attributes to find instances of tgt_type
    results = []
    for attr_name, attr_value in vars(module).items():
        if accept(attr_name, attr_value):
            full_module_path = f'{module_name}.{attr_name}'
            results.append(ModuleVarSpec(var=attr_value, var_path=full_module_path))

    return results


if __name__ == '__main__':
    fire.Fire()
