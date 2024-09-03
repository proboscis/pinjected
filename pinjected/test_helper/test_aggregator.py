import ast
import shelve
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from pprint import pformat
from typing import Callable, Literal, Generic, TypeVar

from beartype import beartype
from loguru import logger

from pinjected.module_inspector import get_project_root, get_module_path
from pinjected.module_var_path import ModuleVarPath


def check_meta_design_variable(file_path):
    with open(file_path, 'r') as file:
        tree = ast.parse(file.read())

    for node in ast.walk(tree):
        if isinstance(node, ast.Global) and '__meta_design__' in node.names:
            return True
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == '__meta_design__':
                    return True

    return False


def meta_design_acceptor(file: Path) -> bool:
    if file.suffix == '.py':
        return check_meta_design_variable(file)
    return False


T = TypeVar("T")


@beartype
@dataclass
class TimeCachedFileData(Generic[T]):
    """
    A class to cache data from files, and return the data if the file is newer than the cache.
    """
    cache_path: Path
    file_to_data: Callable[[Path], T]

    @contextmanager
    def get_cache(self):
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        with shelve.open(str(self.cache_path)) as cache:
            yield cache

    def get_data(self, file: Path) -> T:
        with self.get_cache() as cache:
            key = str(file)
            t = file.stat().st_mtime
            try:
                data, timestamp = cache.get(key, (None, 0))
            except Exception as e:
                logger.warning(f"error while getting cache for {file}: {e}")
                data = None
                timestamp = 0
            if timestamp < t:
                data = self.file_to_data(file)
                cache[key] = (data, t)
            return data


@dataclass
class Annotation:
    name: str
    value: Literal['@injected', '@instance', ':Injected', ':IProxy']


@dataclass
class VariableInFile:
    file_path: Path
    name: str

    def to_module_var_path(self) -> ModuleVarPath:
        root = get_project_root(str(self.file_path))
        module_path = get_module_path(root, self.file_path)
        if module_path.startswith("src."):
            module_path = module_path[4:]
        module_var_path = module_path + '.' + self.name
        return ModuleVarPath(module_var_path)


def find_pinjected_annotations(file_path: str) -> list[Annotation]:
    """
    find pinjected related annotations in a file.
    """
    with open(file_path, 'r') as file:
        tree = ast.parse(file.read())

    results = []

    for node in ast.walk(tree):
        # Check for class, function, and async function definitions
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            # Check for @injected or @instance decorators
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Name) and decorator.id in ['injected', 'instance']:
                    # prefix = 'async ' if isinstance(node, ast.AsyncFunctionDef) else ''
                    results.append(Annotation(f"{node.name}", f'@{decorator.id}'))

        # Check for variable annotations and assignments
        elif isinstance(node, ast.AnnAssign):
            annotation = node.annotation
            if isinstance(annotation, ast.Name):
                if annotation.id in ['Injected', 'IProxy']:
                    results.append(Annotation(node.target.id, f':{annotation.id}'))

        # Check for type comments (for Python 3.5+)
        elif isinstance(node, ast.Assign) and node.type_comment:
            if 'Injected' in node.type_comment or 'IProxy' in node.type_comment:
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        results.append(Annotation(target.id, f':{node.type_comment}'))

    return results


def find_annotated_vars(file_path: Path) -> list[VariableInFile]:
    anns = find_pinjected_annotations(file_path)
    return [VariableInFile(file_path, ann.name) for ann in anns]


def find_run_targets(path: Path) -> list[VariableInFile]:
    if meta_design_acceptor(path):
        return find_annotated_vars(path)
    else:
        return []


def find_test_targets(path: Path) -> list[VariableInFile]:
    run_targets = find_run_targets(path)
    return [target for target in run_targets if target.name.startswith("test_")]


@beartype
@dataclass
class PinjectedTestAggregator:
    cached_data = TimeCachedFileData(
        cache_path=Path("~/.cache/pinjected/test_targets.shelve").expanduser(),
        file_to_data=find_test_targets
    )

    def gather_from_file(self, file: Path) -> list[VariableInFile]:
        return self.cached_data.get_data(file)

    def gather(self, root: Path) -> list[VariableInFile]:
        root = root.expanduser()
        if root.is_file():
            root = root.parent
        logger.info(f"gathering test targets from {root}")
        py_files = list(root.rglob("*.py"))
        logger.info(f"found {len(py_files)} python files")
        targets = []
        for py_file in py_files:
            try:
                accepted = self.cached_data.get_data(py_file)
            except Exception as e:
                logger.warning(f"error while checking {py_file}: {e}")
                continue
            if accepted:
                targets.extend(accepted)
        logger.info(f"found {len(targets)} test targets")
        mvps = [target.to_module_var_path().path for target in targets]
        logger.info(f"test targets:\n {pformat(mvps)}")
        return targets
