import importlib
import os
import sys
from pathlib import Path
from typing import List, Optional, Iterator, Union, Tuple, Dict
from types import ModuleType
from dataclasses import dataclass

from pinjected.module_inspector import get_project_root, ModuleVarSpec
from pinjected.pinjected_logging import logger


class ModuleHelperError(Exception):
    """Base exception for all module helper errors."""
    pass


class InvalidPythonFileError(ModuleHelperError):
    """Raised when a file path is not a valid Python file."""
    pass


class ModulePathError(ModuleHelperError):
    """Raised when there's an issue with module paths."""
    pass


class ModuleLoadError(ModuleHelperError):
    """Raised when a module cannot be loaded."""
    pass


class ModuleAttributeError(ModuleHelperError):
    """Raised when there's an issue extracting an attribute from a module."""
    pass


class SpecialFileError(ModuleHelperError):
    """Raised when there's an issue processing special files."""
    pass


@dataclass(frozen=True)
class DirectoryProcessParams:
    """
    Parameters for processing a directory looking for special files.
    
    Attributes:
        directory: The directory to process
        root_module_path: The root module path to resolve relative paths
        attr_names: List of attribute names to look for in modules
        special_filenames: List of special filenames to look for
        exclude_path: Optional path to exclude from processing
    """
    directory: Path
    root_module_path: Path
    attr_names: List[str]
    special_filenames: List[str]
    exclude_path: Optional[Path] = None


@dataclass(frozen=True)
class ModuleHierarchy:
    """
    Represents a hierarchy of modules from root to target.
    
    Attributes:
        root_module_path: The root module path
        module_paths: Ordered list of module paths from root to target
    """
    root_module_path: Path
    module_paths: List[Path]


def validate_python_file_path(file_path: Path) -> None:
    """
    Validates if a path is a valid Python file.
    
    Args:
        file_path: The file path to validate
        
    Raises:
        TypeError: If file_path is not a Path object
        InvalidPythonFileError: If the file path is not a valid Python file
    """
    if not isinstance(file_path, Path):
        raise TypeError(f"Expected Path object, got {type(file_path)}")
    
    if not file_path.exists():
        raise InvalidPythonFileError(f"File does not exist: {file_path}")
    
    if not file_path.is_file():
        raise InvalidPythonFileError(f"Path is not a file: {file_path}")
    
    if not str(file_path).endswith(".py"):
        raise InvalidPythonFileError(f"File is not a Python file: {file_path}")
    
    logger.trace(f"Validated Python file path: {file_path}")


def validate_directory_path(directory: Path) -> None:
    """
    Validates if a path is a valid directory.
    
    Args:
        directory: The directory path to validate
        
    Raises:
        TypeError: If directory is not a Path object
        SpecialFileError: If the directory is not valid
    """
    if not isinstance(directory, Path):
        raise TypeError(f"directory must be a Path object, got {type(directory)}")
    
    if not directory.exists():
        raise SpecialFileError(f"Directory does not exist: {directory}")
    
    if not directory.is_dir():
        raise SpecialFileError(f"Path is not a directory: {directory}")
    
    logger.trace(f"Validated directory path: {directory}")


def validate_path_under_root(file_path: Path, root_path: Path) -> None:
    """
    Validates if a file path is under a root path.
    
    Args:
        file_path: The file path to check
        root_path: The root path
        
    Raises:
        TypeError: If the inputs are not Path objects
        ModulePathError: If the file path is not under the root path
    """
    if not isinstance(file_path, Path):
        raise TypeError(f"file_path must be a Path object, got {type(file_path)}")
    
    if not isinstance(root_path, Path):
        raise TypeError(f"root_path must be a Path object, got {type(root_path)}")
    
    if not str(file_path).startswith(str(root_path)):
        raise ModulePathError(f"File path {file_path} is not under root path {root_path}")
    
    logger.trace(f"Validated file path {file_path} is under root path {root_path}")


def normalize_special_filenames(
    special_filenames: Optional[Union[str, List[str]]]
) -> List[str]:
    """
    Normalize the special_filenames parameter to ensure it's a list.
    
    Args:
        special_filenames: Either a string or list of strings, or None
        
    Returns:
        A list of special filenames, or empty list if None
        
    Raises:
        TypeError: If special_filenames is not a string, list, or None
    """
    if special_filenames is None:
        return []
    elif isinstance(special_filenames, str):
        return [special_filenames]
    elif isinstance(special_filenames, list):
        if not all(isinstance(item, str) for item in special_filenames):
            raise TypeError("All items in special_filenames list must be strings")
        return special_filenames
    else:
        raise TypeError(f"special_filenames must be a string, list of strings, or None, got {type(special_filenames)}")


def validate_module_paths(file_path: Path, root_module_path: Path) -> None:
    """
    Validates the module paths are valid.
    
    Args:
        file_path: The file path to validate
        root_module_path: The root module path to validate
        
    Raises:
        TypeError: If inputs are not Path objects
        ModulePathError: If root module path is not valid
        InvalidPythonFileError: If file path is not valid
    """
    if not isinstance(file_path, Path):
        raise TypeError(f"file_path must be a Path object, got {type(file_path)}")
    
    if not isinstance(root_module_path, Path):
        raise TypeError(f"root_module_path must be a Path object, got {type(root_module_path)}")
    
    # Path validation
    if not file_path.exists():
        raise InvalidPythonFileError(f"File does not exist: {file_path}")
        
    if not root_module_path.exists():
        raise ModulePathError(f"Root module path does not exist: {root_module_path}")
    
    if not root_module_path.is_dir():
        raise ModulePathError(f"Root module path is not a directory: {root_module_path}")
    
    # Check if file is a Python file
    if not str(file_path).endswith('.py'):
        raise InvalidPythonFileError(f"File is not a Python file: {file_path}")


def get_relative_path(file_path: Path, root_module_path: Path) -> Path:
    """
    Gets the relative path from root_module_path to file_path.
    
    Args:
        file_path: The file path
        root_module_path: The root module path
        
    Returns:
        The relative path
        
    Raises:
        ModulePathError: If file_path is not under root_module_path
    """
    try:
        relative_path = file_path.relative_to(root_module_path)
        return relative_path
    except ValueError:
        raise ModulePathError(f"File path {file_path} is not under root module path {root_module_path}")


def get_module_name(file_path: Path, root_module_path: Path) -> str:
    """
    Determine the module name from a file path relative to the root module path.
    
    Args:
        file_path: The file path to get the module name for
        root_module_path: The root module path
        
    Returns:
        The fully qualified module name
        
    Raises:
        TypeError: If the input parameters are not Path objects
        InvalidPythonFileError: If the file path is not a valid Python file
        ModulePathError: If the file path is not under the root module path 
                         or root path doesn't exist
    """
    # Validate module paths
    validate_module_paths(file_path, root_module_path)
    
    # Get relative path
    relative_path = get_relative_path(file_path, root_module_path)
    
    # Handle src/ pattern common in Python projects
    if str(relative_path).startswith('src/'):
        logger.trace(f"File path starts with src/, removing src/ prefix")
        relative_path = Path(str(relative_path).replace('src/', '', 1))
    
    # Convert path to module name
    module_name = os.path.splitext(str(relative_path).replace(os.sep, '.'))[0]
    logger.trace(f"Created module name: {module_name} from path: {file_path}")
    
    return module_name


def create_module_spec(module_name: str, file_path: Path) -> Tuple[ModuleType, importlib.machinery.ModuleSpec]:
    """
    Creates a module spec from a file path.
    
    Args:
        module_name: The module name to use
        file_path: The file path to import from
        
    Returns:
        A tuple of (module, spec)
        
    Raises:
        ModuleLoadError: If the module specification cannot be created
    """
    # Create spec
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None:
        raise ModuleLoadError(f"Cannot find spec for {module_name} at {file_path}")
        
    # Create module from spec and add to sys.modules
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    
    return module, spec


def load_module_from_path(module_name: str, file_path: Path) -> ModuleType:
    """
    Load a module from a file path.
    
    Args:
        module_name: The module name to use
        file_path: The file path to import from
        
    Returns:
        The loaded module
        
    Raises:
        TypeError: If the inputs are not of the expected types
        InvalidPythonFileError: If the file path is not a valid Python file
        ModuleLoadError: If the module cannot be loaded or executed properly
    """
    # Type validation
    if not isinstance(module_name, str):
        raise TypeError(f"module_name must be a string, got {type(module_name)}")
    
    if not isinstance(file_path, Path):
        raise TypeError(f"file_path must be a Path object, got {type(file_path)}")
    
    # Path validation 
    validate_python_file_path(file_path)
    
    # Return cached module if available
    if module_name in sys.modules:
        logger.debug(f"Using cached module: {module_name}")
        return sys.modules[module_name]
    
    logger.info(f"Importing module: {module_name}")
    
    # Create module and spec
    module, spec = create_module_spec(module_name, file_path)
    
    try:
        # Execute the module
        spec.loader.exec_module(module)
        return module
    except Exception as e:
        # Clean up sys.modules to prevent caching failed module
        if module_name in sys.modules:
            del sys.modules[module_name]
        
        # Re-raise with context
        error_type = type(e).__name__
        if isinstance(e, ValueError):
            raise ModuleLoadError(f"Cannot execute module {module_name} at {file_path}: {e}")
        elif isinstance(e, (ImportError, ModuleNotFoundError)):
            raise ModuleLoadError(f"Cannot import module {module_name} at {file_path}: {e}")
        else:
            raise ModuleLoadError(f"Unexpected error ({error_type}) when loading module {module_name} at {file_path}: {e}")


def extract_module_attribute(
    module: ModuleType, 
    module_name: str, 
    attr_name: str
) -> Optional[ModuleVarSpec]:
    """
    Extract an attribute from a module if it exists.
    
    Args:
        module: The module to extract from
        module_name: The module name
        attr_name: The attribute name to extract
        
    Returns:
        A ModuleVarSpec if the attribute exists, None otherwise
        
    Raises:
        TypeError: If the inputs are not of the expected types
        ModuleAttributeError: If the module is not a valid module type
    """
    # Type validation
    if not isinstance(module, ModuleType):
        raise TypeError(f"module must be a ModuleType, got {type(module)}")
    
    if not isinstance(module_name, str):
        raise TypeError(f"module_name must be a string, got {type(module_name)}")
    
    if not isinstance(attr_name, str):
        raise TypeError(f"attr_name must be a string, got {type(attr_name)}")
    
    if not attr_name:
        raise ModuleAttributeError("attr_name cannot be empty")
    
    # Check for attribute existence
    if hasattr(module, attr_name):
        attr_value = getattr(module, attr_name)
        var_path = f"{module_name}.{attr_name}"
        logger.debug(f"Found attribute '{attr_name}' in module '{module_name}'")
        
        return ModuleVarSpec(
            var=attr_value,
            var_path=var_path,
        )
    
    logger.trace(f"Attribute '{attr_name}' not found in module '{module_name}'")
    return None


def build_parent_path_tree(
    current_path: Path, 
    root_module_path: Path
) -> List[Path]:
    """
    Build a tree of parent paths with __init__.py files.
    
    Args:
        current_path: Current directory path
        root_module_path: Root module path
        
    Returns:
        List of paths to __init__.py files, ordered from root to current
        
    Raises:
        ModulePathError: If path hierarchy is invalid
    """
    path_tree = []
    
    while str(current_path) != str(root_module_path):
        init_file = current_path / "__init__.py"
        if init_file.exists():
            path_tree.insert(0, init_file)
        current_path = current_path.parent
        
        # Safety check to prevent infinite loops
        if not str(current_path).startswith(str(root_module_path)) and str(current_path) != str(root_module_path):
            raise ModulePathError(f"Invalid path hierarchy: {current_path} is not under {root_module_path}")
    
    return path_tree


def build_module_hierarchy(
    file_path: Path,
    root_module_path: Path
) -> ModuleHierarchy:
    """
    Build a hierarchy of modules from root to target file path.
    
    Args:
        file_path: The target file path
        root_module_path: The root module path
        
    Returns:
        A ModuleHierarchy containing the path structure
        
    Raises:
        TypeError: If inputs are not Path objects
        InvalidPythonFileError: If file_path is not a valid Python file
        ModulePathError: If the file path is not under the root module path
                         or if root_module_path is not valid
    """
    # File path validation
    validate_python_file_path(file_path)
    
    # Root path validation
    if not root_module_path.exists():
        raise ModulePathError(f"Root module path does not exist: {root_module_path}")
    
    if not root_module_path.is_dir():
        raise ModulePathError(f"Root module path is not a directory: {root_module_path}")
    
    # Validate file path is under root module path
    validate_path_under_root(file_path, root_module_path)
        
    # Start with the target file
    path_tree = [file_path]
    
    # Build the path from parent directories
    parent_paths = build_parent_path_tree(file_path.parent, root_module_path)
    
    # Insert parent paths at the beginning
    for p in reversed(parent_paths):
        path_tree.insert(0, p)
    
    # Add the root module if it has an __init__.py
    root_init = root_module_path / "__init__.py" 
    if root_init.exists():
        path_tree.insert(0, root_init)
    
    logger.debug(f"Built module path tree: {[str(p) for p in path_tree]}")
    
    return ModuleHierarchy(
        root_module_path=root_module_path,
        module_paths=path_tree
    )


def find_special_files(
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
        
    Raises:
        TypeError: If the inputs are not of the expected types
        SpecialFileError: If the directory does not exist or is not a directory
    """
    # Validate directory
    validate_directory_path(directory)
    
    # Validate special_filenames types
    if not isinstance(special_filenames, list):
        raise TypeError(f"special_filenames must be a list, got {type(special_filenames)}")
    
    for i, filename in enumerate(special_filenames):
        if not isinstance(filename, str):
            raise TypeError(f"special_filenames[{i}] must be a string, got {type(filename)}")
    
    if exclude_path is not None and not isinstance(exclude_path, Path):
        raise TypeError(f"exclude_path must be a Path object, got {type(exclude_path)}")
    
    # Find special files
    special_files = []

    for filename in special_filenames:
        if not filename:
            logger.warning(f"Empty filename in special_filenames - skipping")
            continue
            
        file_path = directory / filename
        if file_path.exists() and (exclude_path is None or file_path != exclude_path):
            logger.debug(f"Found special file: {file_path}")
            special_files.append(file_path)
    
    logger.debug(f"Found {len(special_files)} special files in {directory}")        
    return special_files


def process_special_file(
    special_file_path: Path,
    root_module_path: Path,
    attr_names: List[str]
) -> dict[str, ModuleVarSpec]:
    """
    Process a special file and extract the attributes if they exist.
    
    Args:
        special_file_path: The special file path to process
        root_module_path: The root module path
        attr_names: List of attribute names to look for
        
    Returns:
        A dictionary mapping attribute names to their ModuleVarSpec objects
        (only includes attributes that were found)
        
    Raises:
        TypeError: If the inputs are not of the expected types
        SpecialFileError: If there's an issue processing the special file
    """
    # Type validation
    if not isinstance(special_file_path, Path):
        raise TypeError(f"special_file_path must be a Path object, got {type(special_file_path)}")
    
    if not isinstance(root_module_path, Path):
        raise TypeError(f"root_module_path must be a Path object, got {type(root_module_path)}")
    
    if not isinstance(attr_names, list):
        raise TypeError(f"attr_names must be a list, got {type(attr_names)}")
    
    for i, attr_name in enumerate(attr_names):
        if not isinstance(attr_name, str):
            raise TypeError(f"attr_names[{i}] must be a string, got {type(attr_name)}")
    
    # File validation
    validate_python_file_path(special_file_path)
    
    # Get module name
    special_module_name = get_module_name(special_file_path, root_module_path)
    
    # Import the module
    logger.info(f"Importing special module: {special_module_name}")
    special_module = load_module_from_path(special_module_name, special_file_path)
    
    # Extract the attributes and return results as a dictionary (only include found attributes)
    results = {}
    for attr_name in attr_names:
        attr_spec = extract_module_attribute(special_module, special_module_name, attr_name)
        if attr_spec:
            results[attr_name] = attr_spec
    
    return results


def process_directory(
    params: DirectoryProcessParams
) -> Iterator[ModuleVarSpec]:
    """
    Process a directory for special files and extract attributes.
    
    Args:
        params: The directory processing parameters
        
    Returns:
        An iterator of ModuleVarSpec objects, yielding results in the order
        of attr_names provided in params
        
    Raises:
        TypeError: If the inputs are not of the expected types
        SpecialFileError: If there's an issue with the directory or special files
    """
    # Find special files
    special_files = find_special_files(
        params.directory, 
        params.special_filenames, 
        params.exclude_path
    )
    
    logger.debug(f"Processing {len(special_files)} special files in {params.directory}")
    
    # Process each special file
    results_found = False
    
    for special_file_path in special_files:
        logger.debug(f"Processing special file: {special_file_path}")
        
        try:
            attr_specs = process_special_file(
                special_file_path, 
                params.root_module_path, 
                params.attr_names
            )
            
            # If any attributes were found
            if attr_specs:
                # Yield results in the original attr_names order
                for attr_name in params.attr_names:
                    if attr_name in attr_specs:
                        logger.debug(f"Found attribute {attr_name} in {special_file_path}")
                        results_found = True
                        yield attr_specs[attr_name]
                    else:
                        logger.debug(f"Attribute {attr_name} not found in {special_file_path}")
            else:
                logger.debug(f"No attributes found in {special_file_path}")
        except Exception as e:
            raise SpecialFileError(
                f"Error processing special file {special_file_path} in directory {params.directory}: {e}"
            )
            
    if not results_found:
        logger.info(f"No attributes named {params.attr_names} found in any special files in directory {params.directory}")


def process_parent_module(
    parent_file_path: Path,
    attr_names: List[str],
    root_module_path: Path
) -> dict[str, ModuleVarSpec]:
    """
    Process a parent module to extract attributes.
    
    Args:
        parent_file_path: The parent module file path
        attr_names: List of attribute names to extract
        root_module_path: The root module path
        
    Returns:
        A dictionary mapping attribute names to their ModuleVarSpec objects
        (only includes attributes that were found)
    """
    module_name = get_module_name(parent_file_path, root_module_path)
    module = load_module_from_path(module_name, parent_file_path)
    
    results = {}
    for attr_name in attr_names:
        attr_spec = extract_module_attribute(module, module_name, attr_name)
        if attr_spec:
            results[attr_name] = attr_spec
    
    return results


def walk_parent_modules(
    file_path: Path, 
    attr_names: List[str], 
    root_module_path: Path
) -> Iterator[ModuleVarSpec]:
    """
    Walk from current file's parent directory to root, looking for the attributes
    in each parent module's __init__.py
    
    Args:
        file_path: Path to the target file
        attr_names: List of attribute names to look for
        root_module_path: Root module path
        
    Returns:
        Iterator of ModuleVarSpec objects for found attributes, yielding in the
        same order as attr_names
    """
    parent_dir = file_path.parent
    
    # If we've reached the root module path, stop
    if parent_dir == root_module_path:
        return
    
    # Try the current parent directory's __init__.py
    parent_file_path = parent_dir / '__init__.py'
    if parent_file_path.exists() and parent_file_path != file_path:
        # Process the parent __init__.py
        attr_specs = process_parent_module(parent_file_path, attr_names, root_module_path)
        
        # Yield results in the original attr_names order
        for attr_name in attr_names:
            if attr_name in attr_specs:
                yield attr_specs[attr_name]
        
        # Recursively process grandparents
        yield from walk_parent_modules(parent_file_path, attr_names, root_module_path)
    else:
        # If no __init__.py in current directory, try in grandparent
        grandparent_dir = parent_dir.parent
        if str(grandparent_dir).startswith(str(root_module_path)):
            grandparent_file_path = grandparent_dir / '__init__.py'
            if grandparent_file_path.exists():
                yield from walk_parent_modules(grandparent_file_path, attr_names, root_module_path)


def prepare_module_paths(
    file_path: Path,
    root_module_path: Optional[Path]
) -> Tuple[Path, Path]:
    """
    Prepare and validate the module paths.
    
    Args:
        file_path: The file path to prepare
        root_module_path: The root module path to prepare
        
    Returns:
        A tuple of (file_path, root_module_path) as absolute paths
        
    Raises:
        ModulePathError: If project root cannot be determined
    """
    # Get absolute file path
    file_path = file_path.absolute()
    
    # Determine root module path if not provided
    if root_module_path is None:
        root_path_str = get_project_root(str(file_path))
        if not root_path_str:
            raise ModulePathError(f"Could not determine project root for {file_path}")
        root_module_path = Path(root_path_str)
    
    # Ensure root_module_path is a Path object
    if not isinstance(root_module_path, Path):
        root_module_path = Path(root_module_path)
    
    return file_path, root_module_path.absolute()


def walk_module_attr(
    file_path: Path, 
    attr_names: Union[str, List[str]], 
    root_module_path: Optional[Path] = None
) -> Iterator[ModuleVarSpec]:
    """
    Walk from a root module to the file_path, looking for the attr_names
    and yielding the found variables as ModuleVarSpec
    
    Args:
        file_path: Path to the module file to start searching from
        attr_names: Single attribute name or list of attribute names to look for
        root_module_path: The root module path to use (if None, it will be detected)
        
    Yields:
        ModuleVarSpec objects for found attributes, in the same order as attr_names
        
    Raises:
        TypeError: If file_path is not a Path or attr_names is invalid
        InvalidPythonFileError: If file_path is not a valid Python file
    """
    # Normalize attr_names to list
    attr_names_list = [attr_names] if isinstance(attr_names, str) else attr_names
    
    if not isinstance(attr_names_list, list):
        raise TypeError(f"attr_names must be a string or list, got {type(attr_names)}")
    
    if not attr_names_list:
        raise ValueError("attr_names cannot be empty")
        
    for i, attr_name in enumerate(attr_names_list):
        if not isinstance(attr_name, str):
            raise TypeError(f"attr_names[{i}] must be a string, got {type(attr_name)}")
        if not attr_name:
            raise ValueError(f"attr_names[{i}] cannot be empty")
    
    # Validate file_path
    if not isinstance(file_path, Path):
        raise TypeError(f"file_path must be a Path object, got {type(file_path)}")
    
    # Prepare and validate paths
    file_path, root_module_path = prepare_module_paths(file_path, root_module_path)
    
    # Validate file path
    validate_python_file_path(file_path)
    
    # Check if file is under root module path
    if not str(file_path).startswith(str(root_module_path)):
        logger.error(f"File path {file_path} is not under root module path {root_module_path}")
        return
    
    # Get module name and load the module
    module_name = get_module_name(file_path, root_module_path)
    module = load_module_from_path(module_name, file_path)
    
    # Track seen var_paths to avoid potential duplicates
    seen_var_paths = set()
    
    # Check for attributes in the current module
    for attr_name in attr_names_list:
        attr_spec = extract_module_attribute(module, module_name, attr_name)
        if attr_spec and attr_spec.var_path not in seen_var_paths:
            seen_var_paths.add(attr_spec.var_path)
            yield attr_spec
    
    # Walk up through parent modules with duplicate filtering
    parent_results = yield_unique_results(
        walk_parent_modules(file_path, attr_names_list, root_module_path),
        seen_var_paths
    )
    yield from parent_results


def process_module_hierarchy(
    module_hierarchy: ModuleHierarchy,
    attr_names: List[str],
    special_filenames: List[str]
) -> Iterator[ModuleVarSpec]:
    """
    Process a module hierarchy to find attributes in modules and special files.
    
    Args:
        module_hierarchy: The module hierarchy to process
        attr_names: List of attribute names to look for
        special_filenames: List of special filenames to look for
        
    Returns:
        Iterator of ModuleVarSpec objects, yielding results in the same order as attr_names
        
    Raises:
        ModuleLoadError: If there's an issue loading a module
        ModuleAttributeError: If there's an issue extracting an attribute
        SpecialFileError: If there's an issue processing special files
    """
    # Process each module in the path, from root to target
    for module_path in module_hierarchy.module_paths:
        logger.debug(f"Processing module path: {module_path}")
        
        # Get module name and load module
        module_name = get_module_name(module_path, module_hierarchy.root_module_path)
        module = load_module_from_path(module_name, module_path)
        
        # Check for attributes in the current module (in the specified order)
        for attr_name in attr_names:
            attr_spec = extract_module_attribute(module, module_name, attr_name)
            if attr_spec:
                logger.debug(f"Found attribute {attr_name} in module {module_name}")
                yield attr_spec
        
        # Process special files in the current module's directory
        parent_dir = module_path.parent
        logger.debug(f"Processing directory: {parent_dir}")
        
        # Create parameters for directory processing
        params = DirectoryProcessParams(
            directory=parent_dir,
            root_module_path=module_hierarchy.root_module_path,
            attr_names=attr_names,
            special_filenames=special_filenames,
            exclude_path=module_path  # Don't process the module file itself again
        )
        
        # Process the directory
        yield from process_directory(params)


def validate_attr_params(file_path: Path, attr_names: Union[str, List[str]]) -> List[str]:
    """
    Validate common parameters for attribute search functions and normalize attr_names.
    
    Args:
        file_path: The file path to validate
        attr_names: Single attribute name or list of attribute names to validate
        
    Returns:
        Normalized list of attribute names
        
    Raises:
        TypeError: If inputs are not of the expected types
        ValueError: If attr_names is empty or contains empty strings
    """
    if not isinstance(file_path, Path):
        raise TypeError(f"file_path must be a Path object, got {type(file_path)}")
    
    # Normalize attr_names to list
    attr_names_list = [attr_names] if isinstance(attr_names, str) else attr_names
    
    if not isinstance(attr_names_list, list):
        raise TypeError(f"attr_names must be a string or list, got {type(attr_names)}")
    
    if not attr_names_list:
        raise ValueError("attr_names cannot be empty")
        
    for i, attr_name in enumerate(attr_names_list):
        if not isinstance(attr_name, str):
            raise TypeError(f"attr_names[{i}] must be a string, got {type(attr_name)}")
        if not attr_name:
            raise ValueError(f"attr_names[{i}] cannot be empty")
            
    return attr_names_list


def yield_unique_results(
    results_iterator: Iterator[ModuleVarSpec],
    seen_var_paths: set,
) -> Iterator[ModuleVarSpec]:
    """
    Yield only unique results from an iterator, tracking them in seen_var_paths.
    
    Args:
        results_iterator: Iterator of ModuleVarSpec objects
        seen_var_paths: Set of already seen var_paths
        
    Returns:
        Iterator yielding only previously unseen results
    """
    for result in results_iterator:
        if result.var_path not in seen_var_paths:
            seen_var_paths.add(result.var_path)
            yield result


def walk_module_with_special_files(
    file_path: Path, 
    attr_names: Union[str, List[str]], 
    special_filenames: Optional[Union[str, List[str]]] = ["__pinjected__.py"], 
    root_module_path: Optional[Path] = None
) -> Iterator[ModuleVarSpec]:
    """
    Walk from the root module down to the target file_path, looking for the 
    specified attributes in each module along the path:
    
    1. Start with the top-level module
    2. Check each module along the path to the target file (including special files)
    3. End with the target file
    
    To include __init__.py in the search, add it to special_filenames.
    
    Yields the found variables as ModuleVarSpec, from top module to target file,
    in the same order as the attr_names.
    
    Args:
        file_path: Path to the module file to start searching from
        attr_names: Single attribute name or list of attribute names to look for
        special_filenames: List of filenames to look for in each directory (default: ["__pinjected__.py"])
        root_module_path: The root module path to use (if None, it will be detected)
        
    Returns:
        Iterator of ModuleVarSpec objects, yielding results in the same order as attr_names
        
    Raises:
        TypeError: If the inputs are not of the expected types
        ValueError: If attr_names is empty or contains empty strings
        InvalidPythonFileError: If the file is not a valid Python file
        ModulePathError: If the path structure is invalid
    """
    # Input validation and normalization
    attr_names_list = validate_attr_params(file_path, attr_names)
    special_filenames_list = normalize_special_filenames(special_filenames)
    
    # Get absolute paths
    file_path, root_module_path = prepare_module_paths(file_path, root_module_path)
    
    # Validate file path and check if under root
    validate_python_file_path(file_path)
    logger.trace(f"Project root path: {root_module_path}")
    validate_path_under_root(file_path, root_module_path)
    
    # Build module hierarchy
    module_hierarchy = build_module_hierarchy(file_path, root_module_path)
    logger.debug(f"Built module hierarchy with {len(module_hierarchy.module_paths)} paths")
    
    # Track yielded var_paths to avoid duplicates
    seen_var_paths = set()
    has_yielded_results = False
    
    # Process root directory first
    logger.debug(f"Processing root directory: {root_module_path}")
    
    # Create parameters for root directory processing
    root_params = DirectoryProcessParams(
        directory=root_module_path,
        root_module_path=root_module_path,
        attr_names=attr_names_list,
        special_filenames=special_filenames_list
    )
    
    # Process the root directory with duplicate filtering
    root_results = yield_unique_results(process_directory(root_params), seen_var_paths)
    for result in root_results:
        has_yielded_results = True
        yield result
    
    # Process the module hierarchy with duplicate filtering
    hierarchy_results = yield_unique_results(
        process_module_hierarchy(
            module_hierarchy=module_hierarchy,
            attr_names=attr_names_list,
            special_filenames=special_filenames_list
        ),
        seen_var_paths
    )
    for result in hierarchy_results:
        has_yielded_results = True
        yield result
    
    if not has_yielded_results:
        logger.info(f"No attributes named {attr_names_list} found in any module or special file")