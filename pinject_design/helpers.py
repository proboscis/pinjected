import importlib
import os
import sys
from pathlib import Path
from typing import Optional, List

from returns.maybe import maybe

from pinject_design import injected_function, Injected, Designed, Design
from pinject_design.di.app_injected import InjectedEvalContext
from pinject_design.di.proxiable import DelegatedVar
from pinject_design.module_inspector import ModuleVarSpec, inspect_module_for_type, get_project_root
from pinject_design.helper_structure import IdeaRunConfigurations, MetaContext


@injected_function
def inspect_and_make_configurations(
        injected_to_idea_configs,
        logger,
        /,
        module_path
) -> IdeaRunConfigurations:
    runnables = get_runnables(module_path)
    logger.info(f"Found {len(runnables)} injecteds")
    results = dict()
    logger.info(f"found {len(runnables)} injecteds")
    for tgt in runnables:
        if isinstance(tgt, ModuleVarSpec):
            results.update(injected_to_idea_configs(tgt).configs)
    return IdeaRunConfigurations(configs=results)


def load_variable_by_module_path(full_module_path):
    from loguru import logger
    logger.info(f"loading {full_module_path}")
    module_path_parts = full_module_path.split('.')
    variable_name = module_path_parts[-1]
    module_path = '.'.join(module_path_parts[:-1])

    # Import the module
    module = importlib.import_module(module_path)

    # Retrieve the variable using getattr()
    variable = getattr(module, variable_name)

    return variable


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
    assert design_paths
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


def get_runnables(module_path) -> List[ModuleVarSpec]:
    def accept(name, tgt):
        match (name, tgt):
            case (n, _) if n.startswith("provide"):
                return True
            case (_, Injected()):
                return True
            case (_, Designed()):
                return True
            case (_, DelegatedVar(value, cxt)) if cxt == InjectedEvalContext:
                return True
            case (_, DelegatedVar(value, cxt)):
                return False
            case (_, item) if hasattr(item, "__runnable_metadata__") and isinstance(item.__runnable_metadata__, dict):
                return True
            case _:
                return False

    runnables = inspect_module_for_type(module_path, accept)
    return runnables


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


def walk_module_attr(file_path: Path, attr_name, root_module_path=None):
    """
    walk down from a root module to the file_path, while looking for the attr_name and yielding the found variable as ModuleVarSpec
    :param file_path:
    :param attr_name:
    :return:
    """
    from loguru import logger
    if root_module_path is None:
        root_module_path = Path(get_project_root(str(file_path)))
    if not str(file_path).startswith(str(root_module_path)):
        return

    relative_path = file_path.relative_to(root_module_path)
    module_name = os.path.splitext(str(relative_path).replace(os.sep, '.'))[0]
    if module_name not in sys.modules:
        logger.info(f"importing module: {module_name}")
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
    module = sys.modules[module_name]
    if hasattr(module, attr_name):
        yield ModuleVarSpec(
            var=getattr(module, attr_name),
            var_path=module_name + '.' + attr_name,
        )

    parent_dir = file_path.parent
    if parent_dir != root_module_path:
        parent_file_path = parent_dir / '__init__.py'
        if parent_file_path.exists() and parent_file_path != file_path:
            yield from walk_module_attr(parent_file_path, attr_name, root_module_path)
        else:
            grandparent_dir = parent_dir.parent
            grandparent_file_path = grandparent_dir / '__init__.py'
            if grandparent_file_path.exists():
                yield from walk_module_attr(grandparent_file_path, attr_name, root_module_path)


def gather_meta_design(file_path: Path, meta_design_name: str = "__meta_design__") -> MetaContext:
    designs = list(walk_module_attr(file_path, meta_design_name))
    designs.reverse()
    res = Design()
    for item in designs:
        res = res + item.var
    return MetaContext(
        trace=designs,
        accumulated=res
    )
