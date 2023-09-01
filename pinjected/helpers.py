import ast

import importlib
import sys
from dataclasses import dataclass, field
from pathlib import Path
from returns.maybe import maybe
from typing import Optional, List

from pinjected import injected_function, Injected, Designed
from pinjected.di.app_injected import InjectedEvalContext
from pinjected.di.proxiable import DelegatedVar
from pinjected.helper_structure import IdeaRunConfigurations
from pinjected.maybe_patch import patch_maybe
from pinjected.module_helper import walk_module_attr
from pinjected.module_inspector import ModuleVarSpec, inspect_module_for_type
patch_maybe()

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



def find_var_or_func_definition_code_in_module(module_dot_path, name):
    try:
        module = importlib.import_module(module_dot_path)
    except ImportError:
        return f"Module {module_dot_path} could not be imported."

    module_file_path = module.__file__

    if module_file_path.endswith('.pyc'):
        module_file_path = module_file_path[:-1]  # convert .pyc to .py

    with open(module_file_path, 'r') as f:
        lines = f.readlines()
        tree = ast.parse(''.join(lines))

    definition = None

    for node in ast.walk(tree):
        if definition is None and isinstance(node, (ast.Assign, ast.AnnAssign, ast.FunctionDef,ast.AsyncFunctionDef)):
            targets = []
            if isinstance(node, ast.Assign):
                targets = node.targets
            elif isinstance(node, ast.AnnAssign):
                targets = [node.target]

            for target in targets:
                if isinstance(target, ast.Name) and target.id == name:
                    start_line = node.lineno  # 1-based index
                    end_line = getattr(node, 'end_lineno', start_line)  # Some older Python versions don't have end_lineno
                    definition = ''.join(lines[start_line - 1:end_line]).strip()

            if isinstance(node, (ast.FunctionDef,ast.AsyncFunctionDef)) and node.name == name:
                start_line = node.lineno
                end_line = getattr(node, 'end_lineno', start_line)
                definition = ''.join(lines[start_line - 1:end_line]).strip()

    if definition:
        return definition
    else:
        raise RuntimeError(f"{name} is not defined in the given module: {module_dot_path}")


def find_import_statements_in_module(module_dot_path):
    try:
        module = importlib.import_module(module_dot_path)
    except ImportError:
        return f"Module {module_dot_path} could not be imported."

    module_file_path = module.__file__

    if module_file_path.endswith('.pyc'):
        module_file_path = module_file_path[:-1]  # convert .pyc to .py

    with open(module_file_path, 'r') as f:
        lines = f.readlines()
        tree = ast.parse(''.join(lines))

    import_statements = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            start_line = node.lineno
            end_line = getattr(node, 'end_lineno', start_line)
            import_statements.append(''.join(lines[start_line - 1:end_line]).strip())

    return import_statements
@dataclass
class ModuleVarPath:
    """
    represents a path where a variable is defined.
    like a.b.c.d
    """
    path: str

    def __post_init__(self):
        assert self.module_name is not None
        assert self.var_name is not None

    def load(self):
        return load_variable_by_module_path(self.path)

    @property
    def module_name(self):
        module = ".".join(self.path.split(".")[:-1])
        return module

    @property
    def var_name(self):
        return self.path.split(".")[-1]

    def to_import_line(self):
        return f"from {self.module_name} import {self.var_name}"

    @property
    def module_file_path(self):
        return sys.modules[self.module_name].__file__

    @staticmethod
    def from_local_variable(var_name):
        # get parent frame
        # then return a ModulePath
        raise NotImplementedError

    def definition_snippet(self):
        """
        returns a code snippet that defines the variable
        :return:
        """
        return find_var_or_func_definition_code_in_module(self.module_name, self.var_name)

    def depending_import_lines(self):
        return find_import_statements_in_module(self.module_name)


@dataclass
class RunnableSpec:
    tgt_path: ModuleVarPath
    design_path: ModuleVarPath = field(default_factory=lambda:ModuleVarPath("pinjected.di.util.EmptyDesign"))

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


