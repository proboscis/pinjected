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
    from pinjected.pinjected_logging import logger
    if root_module_path is None:
        root_module_path = Path(get_project_root(str(file_path)))
    file_path = file_path.absolute()
    assert str(file_path).endswith(".py"), f"a python file path must be provided, got:{file_path}"
    logger.trace(f"project root path:{root_module_path}")
    if not str(file_path).startswith(str(root_module_path)):
        # logger.error(f"file path {file_path} is not under root module path {root_module_path}")
        return

    relative_path = file_path.relative_to(root_module_path)
    if str(relative_path).startswith('src/'):
        logger.trace(f"file_path starts with src/")
        relative_path = Path(str(relative_path).replace('src/', '',1))
    logger.trace(f"relative path:{relative_path}")
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


def walk_module_with_special_files(file_path: Path, attr_name, special_filenames=None, root_module_path=None):
    """
    Walk up from a file_path to the root module, looking for the specified attribute in:
    1. The current file
    2. Any special files in each directory (configurable via special_filenames)
    
    To include __init__.py in the search, add it to special_filenames.
    
    Yields the found variables as ModuleVarSpec.
    
    :param file_path: Path to the module file to start searching from
    :param attr_name: The attribute name to look for
    :param special_filenames: List of filenames to look for in each directory (default: ["__pinjected__.py"])
    :param root_module_path: The root module path to use (if None, it will be detected)
    :return: Generator of ModuleVarSpec objects
    """
    from pinjected.pinjected_logging import logger
    
    # Default to __pinjected__.py if no filenames provided
    if special_filenames is None:
        special_filenames = ["__pinjected__.py"]
    # Convert single string to list
    elif isinstance(special_filenames, str):
        special_filenames = [special_filenames]
    
    if root_module_path is None:
        root_module_path = Path(get_project_root(str(file_path)))
    file_path = file_path.absolute()
    assert str(file_path).endswith(".py"), f"a python file path must be provided, got:{file_path}"
    logger.trace(f"project root path:{root_module_path}")
    if not str(file_path).startswith(str(root_module_path)):
        return

    # Process the current file
    relative_path = file_path.relative_to(root_module_path)
    if str(relative_path).startswith('src/'):
        logger.trace(f"file_path starts with src/")
        relative_path = Path(str(relative_path).replace('src/', '', 1))
    logger.trace(f"relative path:{relative_path}")
    module_name = os.path.splitext(str(relative_path).replace(os.sep, '.'))[0]
    
    # Import and process the current module
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
    
    # If the attribute exists in this module, yield it
    if hasattr(module, attr_name):
        yield ModuleVarSpec(
            var=getattr(module, attr_name),
            var_path=module_name + '.' + attr_name,
        )

    # Check for special files in the current directory
    parent_dir = file_path.parent
    
    for special_filename in special_filenames:
        special_file_path = parent_dir / special_filename
        if special_file_path.exists() and special_file_path != file_path:
            # Determine module name for the special file
            special_rel_path = special_file_path.relative_to(root_module_path)
            if str(special_rel_path).startswith('src/'):
                special_rel_path = Path(str(special_rel_path).replace('src/', '', 1))
            special_module_name = os.path.splitext(str(special_rel_path).replace(os.sep, '.'))[0]
            
            # Import the special module
            try:
                logger.info(f"importing special module: {special_module_name}")
                spec = importlib.util.spec_from_file_location(special_module_name, special_file_path)
                if spec is not None:
                    if special_module_name in sys.modules:
                        special_module = sys.modules[special_module_name]
                    else:
                        special_module = importlib.util.module_from_spec(spec)
                        sys.modules[special_module_name] = special_module
                        try:
                            spec.loader.exec_module(special_module)
                        except ValueError as e:
                            logger.error(f"cannot exec special module {special_module_name} at {special_file_path} due to {e}")
                            continue
                    
                    # If the attribute exists in the special module, yield it
                    if hasattr(special_module, attr_name):
                        logger.debug(f"Found {attr_name} in {special_module_name}")
                        yield ModuleVarSpec(
                            var=getattr(special_module, attr_name),
                            var_path=special_module_name + '.' + attr_name,
                        )
            except Exception as e:
                logger.error(f"Error processing special file {special_file_path}: {e}")
    
    # Continue walking up the directory structure
    if parent_dir != root_module_path:
        # Find a file in the parent directory to continue the walk
        parent_init_path = None
        
        # Use the first matching file in special_filenames in the parent directory for upward recursion
        for special_filename in special_filenames:
            possible_parent_file = parent_dir.parent / special_filename
            if possible_parent_file.exists():
                parent_init_path = possible_parent_file
                break
        
        # If we found a file to continue with, recurse upward
        if parent_init_path is not None:
            yield from walk_module_with_special_files(parent_init_path, attr_name, special_filenames, root_module_path)
