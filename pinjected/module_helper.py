import importlib

import sys

import os

from pathlib import Path

from pinjected.module_inspector import get_project_root, ModuleVarSpec


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
    file_path = file_path.absolute()
    assert str(file_path).endswith(".py"), f"a python file path must be provided, got:{file_path}"
    logger.debug(f"project root path:{root_module_path}")
    if not str(file_path).startswith(str(root_module_path)):
        # logger.error(f"file path {file_path} is not under root module path {root_module_path}")
        return

    relative_path = file_path.relative_to(root_module_path)
    if str(relative_path).startswith('src/'):
        logger.warning(f"file_path starts with src/")
        relative_path = Path(str(relative_path).replace('src/', '',1))
    logger.debug(f"relative path:{relative_path}")
    module_name = os.path.splitext(str(relative_path).replace(os.sep, '.'))[0]
    if module_name not in sys.modules:
        logger.info(f"importing module: {module_name}")
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None:
            logger.error(f"cannot find spec for {module_name} at {file_path}")
            return
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        try:
            spec.loader.exec_module(module)
        except ValueError as e:
            logger.error(f"cannot exec module {module_name} at {file_path} due to {e}, \n source=\n{file_path.read_text()}")
            raise e
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
