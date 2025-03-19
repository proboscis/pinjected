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


from typing import List, Optional, Iterator, Union, Any


def _normalize_special_filenames(
    special_filenames: Optional[Union[str, List[str]]]
) -> List[str]:
    """
    Normalize the special_filenames parameter to ensure it's a list.
    
    Args:
        special_filenames: Either a string or list of strings, or None
        
    Returns:
        A list of special filenames, or empty list if None
    """
    if special_filenames is None:
        return []
    elif isinstance(special_filenames, str):
        return [special_filenames]
    return special_filenames


def _get_module_name(file_path: Path, root_module_path: Path) -> str:
    """
    Determine the module name from a file path relative to the root module path.
    
    Args:
        file_path: The file path to get the module name for
        root_module_path: The root module path
        
    Returns:
        The module name
    """
    relative_path = file_path.relative_to(root_module_path)
    
    # Handle src/ pattern common in Python projects
    if str(relative_path).startswith('src/'):
        relative_path = Path(str(relative_path).replace('src/', '', 1))
        
    return os.path.splitext(str(relative_path).replace(os.sep, '.'))[0]


def _import_module_from_path(module_name: str, file_path: Path) -> Optional[Any]:
    """
    Import a module from a file path.
    
    Args:
        module_name: The module name to use
        file_path: The file path to import from
        
    Returns:
        The imported module or None if import failed
    """
    from pinjected.pinjected_logging import logger
    
    if module_name in sys.modules:
        return sys.modules[module_name]
    
    logger.info(f"importing module: {module_name}")
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    
    if spec is None:
        logger.error(f"cannot find spec for {module_name} at {file_path}")
        return None
        
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    
    try:
        spec.loader.exec_module(module)
        return module
    except ValueError as e:
        logger.error(f"cannot exec module {module_name} at {file_path} due to {e}, \n source=\n{file_path.read_text()}")
        raise e


def _extract_attribute(module: Any, module_name: str, attr_name: str) -> Optional[ModuleVarSpec]:
    """
    Extract an attribute from a module if it exists.
    
    Args:
        module: The module to extract from
        module_name: The module name
        attr_name: The attribute name to extract
        
    Returns:
        A ModuleVarSpec if the attribute exists, None otherwise
    """
    if hasattr(module, attr_name):
        return ModuleVarSpec(
            var=getattr(module, attr_name),
            var_path=f"{module_name}.{attr_name}",
        )
    return None


def _find_first_special_file_in_parent(
    parent_dir: Path, 
    special_filenames: List[str],
    root_module_path: Path
) -> Optional[Path]:
    """
    Find the first special file that exists in the parent directory.
    
    Args:
        parent_dir: The parent directory
        special_filenames: List of special filenames to look for
        root_module_path: The root module path
        
    Returns:
        The path to the first special file found, or None
    """
    for special_filename in special_filenames:
        possible_parent_file = parent_dir.parent / special_filename
        if possible_parent_file.exists():
            return possible_parent_file
    return None


def _build_module_path_tree(
    file_path: Path,
    root_module_path: Path
) -> List[Path]:
    """
    Build a list of module paths from the root module to the target file path.
    
    Args:
        file_path: The target file path
        root_module_path: The root module path
        
    Returns:
        A list of paths from the root (first) to the target (last)
    """
    from pinjected.pinjected_logging import logger
    
    if not str(file_path).startswith(str(root_module_path)):
        return []
        
    # Start with the target file
    path_tree = [file_path]
    
    # Build the path from root to target
    current_path = file_path.parent
    while str(current_path) != str(root_module_path):
        init_file = current_path / "__init__.py"
        if init_file.exists():
            path_tree.insert(0, init_file)
        current_path = current_path.parent
        
    # Add the root module if it has an __init__.py
    root_init = root_module_path / "__init__.py" 
    if root_init.exists():
        path_tree.insert(0, root_init)
    
    # Ensure the correct ordering by fully traversing all levels    
    logger.debug(f"Built module path tree: {[str(p) for p in path_tree]}")
    
    return path_tree


def _find_special_files_in_dir(
    directory: Path,
    special_filenames: List[str],
    exclude_path: Optional[Path] = None
) -> List[Path]:
    """
    Find all special files in a directory.
    
    Args:
        directory: The directory to search in
        special_filenames: The special filenames to look for
        exclude_path: An optional path to exclude from the results
        
    Returns:
        A list of paths to the special files
    """
    special_files = []
    
    for filename in special_filenames:
        file_path = directory / filename
        if file_path.exists() and (exclude_path is None or file_path != exclude_path):
            special_files.append(file_path)
            
    return special_files


def _process_module_directory(
    directory: Path,
    root_module_path: Path,
    attr_name: str,
    special_filenames: List[str],
    exclude_path: Optional[Path] = None
) -> Iterator[ModuleVarSpec]:
    """
    Process a directory for special files and extract attributes.
    
    Args:
        directory: The directory to process
        root_module_path: The root module path
        attr_name: The attribute name to look for
        special_filenames: List of special filenames to look for
        exclude_path: Optional path to exclude
        
    Returns:
        Iterator of ModuleVarSpec objects
    """
    from pinjected.pinjected_logging import logger
    
    # Find and process all special files in this directory
    special_files = _find_special_files_in_dir(directory, special_filenames, exclude_path)
    
    for special_file_path in special_files:
        attr_spec = _process_special_file(special_file_path, root_module_path, attr_name)
        if attr_spec:
            yield attr_spec


def _process_special_file(
    special_file_path: Path,
    root_module_path: Path,
    attr_name: str
) -> Optional[ModuleVarSpec]:
    """
    Process a special file and extract the attribute if it exists.
    
    Args:
        special_file_path: The special file path to process
        root_module_path: The root module path
        attr_name: The attribute name to look for
        
    Returns:
        A ModuleVarSpec if the attribute is found, None otherwise
    """
    from pinjected.pinjected_logging import logger
    
    special_module_name = _get_module_name(special_file_path, root_module_path)
    
    try:
        logger.info(f"importing special module: {special_module_name}")
        special_module = _import_module_from_path(special_module_name, special_file_path)
        
        if special_module and hasattr(special_module, attr_name):
            logger.debug(f"Found {attr_name} in {special_module_name}")
            return ModuleVarSpec(
                var=getattr(special_module, attr_name),
                var_path=f"{special_module_name}.{attr_name}",
            )
    except Exception as e:
        logger.error(f"Error processing special file {special_file_path}: {e}")
    
    return None


def walk_module_with_special_files(
    file_path: Path, 
    attr_name: str, 
    special_filenames: Optional[Union[str, List[str]]] = ["__pinjected__.py"], 
    root_module_path: Optional[Path] = None
) -> Iterator[ModuleVarSpec]:
    """
    Walk from the root module down to the target file_path, looking for the 
    specified attribute in each module along the path:
    
    1. Start with the top-level module
    2. Check each module along the path to the target file (including special files)
    3. End with the target file
    
    To include __init__.py in the search, add it to special_filenames.
    
    Yields the found variables as ModuleVarSpec, from top module to target file.
    
    Args:
        file_path: Path to the module file to start searching from
        attr_name: The attribute name to look for
        special_filenames: List of filenames to look for in each directory (default: ["__pinjected__.py"])
        root_module_path: The root module path to use (if None, it will be detected)
        
    Returns:
        Generator of ModuleVarSpec objects
    """
    from pinjected.pinjected_logging import logger
    
    # Normalize parameters
    special_filenames_list = _normalize_special_filenames(special_filenames)
    
    if root_module_path is None:
        root_module_path = Path(get_project_root(str(file_path)))
        
    file_path = file_path.absolute()
    assert str(file_path).endswith(".py"), f"a python file path must be provided, got:{file_path}"
    
    logger.trace(f"project root path:{root_module_path}")
    
    # Validate file path
    if not str(file_path).startswith(str(root_module_path)):
        return

    # Build path tree from root to target
    module_path_tree = _build_module_path_tree(file_path, root_module_path)
    
    # Check for special files at the root level first
    yield from _process_module_directory(
        root_module_path, 
        root_module_path, 
        attr_name, 
        special_filenames_list
    )
    
    # Process each module in the path, from root to target
    for module_path in module_path_tree:
        # Process the current module
        module_name = _get_module_name(module_path, root_module_path)
        module = _import_module_from_path(module_name, module_path)
        
        if module is None:
            continue
            
        # Check for attribute in the current module
        attr_spec = _extract_attribute(module, module_name, attr_name)
        if attr_spec:
            yield attr_spec
        
        # Process special files in the current directory
        parent_dir = module_path.parent
        yield from _process_module_directory(
            parent_dir, 
            root_module_path, 
            attr_name, 
            special_filenames_list, 
            module_path
        )
