import ast
import importlib
import sys
from dataclasses import dataclass


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

    logger.info(f"loaded {full_module_path}")

    return variable


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
