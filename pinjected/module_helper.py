import importlib
import os
import sys
from pathlib import Path
from typing import List, Optional, Iterator, Union, Any, Tuple
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


@dataclass(frozen=True)
class DirectoryProcessParams:
    """
    Parameters for processing a directory looking for special files.
    
    Attributes:
        directory: The directory to process
        root_module_path: The root module path to resolve relative paths
        attr_name: The attribute name to look for in modules
        special_filenames: List of special filenames to look for
        exclude_path: Optional path to exclude from processing
    """
    directory: Path
    root_module_path: Path
    attr_name: str
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
    # Type validation
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
    
    # Check if the file is under the root path
    try:
        relative_path = file_path.relative_to(root_module_path)
    except ValueError:
        raise ModulePathError(f"File path {file_path} is not under root module path {root_module_path}")
    
    # Handle src/ pattern common in Python projects
    if str(relative_path).startswith('src/'):
        logger.trace(f"File path starts with src/, removing src/ prefix")
        relative_path = Path(str(relative_path).replace('src/', '', 1))
    
    # Convert path to module name
    module_name = os.path.splitext(str(relative_path).replace(os.sep, '.'))[0]
    logger.trace(f"Created module name: {module_name} from path: {file_path}")
    
    return module_name


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
    if not file_path.exists():
        raise InvalidPythonFileError(f"File does not exist: {file_path}")
    
    if not file_path.is_file():
        raise InvalidPythonFileError(f"Path is not a file: {file_path}")
    
    if not str(file_path).endswith('.py'):
        raise InvalidPythonFileError(f"File is not a Python file: {file_path}")
    
    # Return cached module if available
    if module_name in sys.modules:
        logger.debug(f"Using cached module: {module_name}")
        return sys.modules[module_name]
    
    logger.info(f"Importing module: {module_name}")
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    
    if spec is None:
        error_msg = f"Cannot find spec for {module_name} at {file_path}"
        logger.error(error_msg)
        raise ModuleLoadError(error_msg)
        
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    
    try:
        spec.loader.exec_module(module)
        return module
    except ValueError as e:
        error_msg = f"Cannot execute module {module_name} at {file_path}: {e}"
        logger.error(f"{error_msg}\nSource:\n{file_path.read_text()}")
        # Clean up sys.modules to prevent caching the failed module
        if module_name in sys.modules:
            del sys.modules[module_name]
        raise ModuleLoadError(error_msg) from e
    except (ImportError, ModuleNotFoundError) as e:
        error_msg = f"Cannot import module {module_name} at {file_path}: {e}"
        logger.error(error_msg)
        # Clean up sys.modules to prevent caching the failed module
        if module_name in sys.modules:
            del sys.modules[module_name]
        raise ModuleLoadError(error_msg) from e
    except Exception as e:
        error_msg = f"Unexpected error when loading module {module_name} at {file_path}: {e}"
        logger.error(error_msg)
        # Clean up sys.modules to prevent caching the failed module
        if module_name in sys.modules:
            del sys.modules[module_name]
        raise ModuleLoadError(error_msg) from e


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
        try:
            attr_value = getattr(module, attr_name)
            var_path = f"{module_name}.{attr_name}"
            logger.debug(f"Found attribute '{attr_name}' in module '{module_name}'")
            
            return ModuleVarSpec(
                var=attr_value,
                var_path=var_path,
            )
        except Exception as e:
            error_msg = f"Error extracting attribute '{attr_name}' from module '{module_name}': {e}"
            logger.error(error_msg)
            raise ModuleAttributeError(error_msg) from e
    
    logger.trace(f"Attribute '{attr_name}' not found in module '{module_name}'")
    return None


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
    # Input validation
    if not isinstance(file_path, Path):
        raise TypeError(f"file_path must be a Path object, got {type(file_path)}")
    
    if not isinstance(root_module_path, Path):
        raise TypeError(f"root_module_path must be a Path object, got {type(root_module_path)}")
    
    # File path validation
    if not file_path.exists():
        raise InvalidPythonFileError(f"File does not exist: {file_path}")
    
    if not file_path.is_file():
        raise InvalidPythonFileError(f"Path is not a file: {file_path}")
    
    if not str(file_path).endswith('.py'):
        raise InvalidPythonFileError(f"File is not a Python file: {file_path}")
    
    # Root path validation
    if not root_module_path.exists():
        raise ModulePathError(f"Root module path does not exist: {root_module_path}")
    
    if not root_module_path.is_dir():
        raise ModulePathError(f"Root module path is not a directory: {root_module_path}")
    
    # Validate file path is under root module path
    if not str(file_path).startswith(str(root_module_path)):
        raise ModulePathError(f"File path {file_path} is not under root module path {root_module_path}")
        
    # Start with the target file
    path_tree = [file_path]
    
    # Build the path from root to target
    current_path = file_path.parent
    while str(current_path) != str(root_module_path):
        init_file = current_path / "__init__.py"
        if init_file.exists():
            path_tree.insert(0, init_file)
        current_path = current_path.parent
        
        # Safety check to prevent infinite loops (should never happen based on the startswith check above)
        if not str(current_path).startswith(str(root_module_path)) and str(current_path) != str(root_module_path):
            # This should be unreachable given the validation above, but included as a safeguard
            raise ModulePathError(f"Invalid path hierarchy: {current_path} is not under {root_module_path}")
    
    # Add the root module if it has an __init__.py
    root_init = root_module_path / "__init__.py" 
    if root_init.exists():
        path_tree.insert(0, root_init)
    
    # Ensure the correct ordering by fully traversing all levels    
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
        SpecialFileError: If the directory does not exist or is not a directory,
                          or if there's an issue finding the special files
    """
    # Type validation
    if not isinstance(directory, Path):
        raise TypeError(f"directory must be a Path object, got {type(directory)}")
    
    if not isinstance(special_filenames, list):
        raise TypeError(f"special_filenames must be a list, got {type(special_filenames)}")
    
    # Validate all filenames are strings
    for i, filename in enumerate(special_filenames):
        if not isinstance(filename, str):
            raise TypeError(f"special_filenames[{i}] must be a string, got {type(filename)}")
    
    if exclude_path is not None and not isinstance(exclude_path, Path):
        raise TypeError(f"exclude_path must be a Path object, got {type(exclude_path)}")
    
    # Directory validation
    if not directory.exists():
        raise SpecialFileError(f"Directory does not exist: {directory}")
    
    if not directory.is_dir():
        raise SpecialFileError(f"Path is not a directory: {directory}")
    
    # Find special files
    special_files = []
    
    for filename in special_filenames:
        if not filename:
            logger.warning(f"Empty filename in special_filenames - skipping")
            continue
            
        try:
            file_path = directory / filename
            if file_path.exists() and (exclude_path is None or file_path != exclude_path):
                logger.debug(f"Found special file: {file_path}")
                special_files.append(file_path)
        except Exception as e:
            # This could happen if there's an issue with the directory / filename combination
            error_msg = f"Error checking for special file '{filename}' in directory '{directory}': {e}"
            logger.error(error_msg)
            raise SpecialFileError(error_msg) from e
    
    logger.debug(f"Found {len(special_files)} special files in {directory}")        
    return special_files


def process_directory(
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
        exclude_path: An optional path to exclude from the results
        
    Returns:
        An iterator of ModuleVarSpec objects
        
    Raises:
        TypeError: If the inputs are not of the expected types
        SpecialFileError: If there's an issue with the directory or special files
    """
    # Type validation
    if not isinstance(directory, Path):
        raise TypeError(f"directory must be a Path object, got {type(directory)}")
    
    if not isinstance(root_module_path, Path):
        raise TypeError(f"root_module_path must be a Path object, got {type(root_module_path)}")
    
    if not isinstance(attr_name, str):
        raise TypeError(f"attr_name must be a string, got {type(attr_name)}")
    
    if not isinstance(special_filenames, list):
        raise TypeError(f"special_filenames must be a list, got {type(special_filenames)}")
    
    # Find special files
    try:
        special_files = find_special_files(directory, special_filenames, exclude_path)
        logger.debug(f"Processing {len(special_files)} special files in {directory}")
    except (TypeError, SpecialFileError) as e:
        error_msg = f"Failed to find special files in directory {directory}: {e}"
        logger.error(error_msg)
        raise SpecialFileError(error_msg) from e
    
    # Process each special file and collect results
    results_found = False
    
    for special_file_path in special_files:
        logger.debug(f"Processing special file: {special_file_path}")
        
        try:
            attr_spec = process_special_file(
                special_file_path, 
                root_module_path, 
                attr_name
            )
            
            if attr_spec:
                logger.debug(f"Found attribute {attr_name} in {special_file_path}")
                results_found = True
                yield attr_spec
            else:
                logger.debug(f"Attribute {attr_name} not found in {special_file_path}")
                
        except SpecialFileError as e:
            # We'll re-raise with added context about the directory we're processing
            error_msg = f"Error processing special file {special_file_path} in directory {directory}: {e}"
            logger.error(error_msg)
            raise SpecialFileError(error_msg) from e
            
    if not results_found:
        logger.info(f"No attributes named '{attr_name}' found in any special files in directory {directory}")


def process_special_file(
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
        
    Raises:
        TypeError: If the inputs are not of the expected types
        SpecialFileError: If there's an issue processing the special file
    """
    # Type validation
    if not isinstance(special_file_path, Path):
        raise TypeError(f"special_file_path must be a Path object, got {type(special_file_path)}")
    
    if not isinstance(root_module_path, Path):
        raise TypeError(f"root_module_path must be a Path object, got {type(root_module_path)}")
    
    if not isinstance(attr_name, str):
        raise TypeError(f"attr_name must be a string, got {type(attr_name)}")
    
    # File validation
    try:
        validate_python_file_path(special_file_path)
    except (TypeError, InvalidPythonFileError) as e:
        error_msg = f"Invalid special file path: {e}"
        logger.error(error_msg)
        raise SpecialFileError(error_msg) from e
    
    # Get module name
    try:
        special_module_name = get_module_name(special_file_path, root_module_path)
    except (TypeError, InvalidPythonFileError, ModulePathError) as e:
        error_msg = f"Failed to get module name for {special_file_path}: {e}"
        logger.error(error_msg)
        raise SpecialFileError(error_msg) from e
    
    # Import the module
    try:
        logger.info(f"Importing special module: {special_module_name}")
        special_module = load_module_from_path(special_module_name, special_file_path)
    except (TypeError, InvalidPythonFileError, ModuleLoadError) as e:
        error_msg = f"Failed to import module {special_module_name} from {special_file_path}: {e}"
        logger.error(error_msg)
        raise SpecialFileError(error_msg) from e
    
    # Extract the attribute
    try:
        return extract_module_attribute(special_module, special_module_name, attr_name)
    except (TypeError, ModuleAttributeError) as e:
        error_msg = f"Failed to extract attribute {attr_name} from module {special_module_name}: {e}"
        logger.error(error_msg)
        raise SpecialFileError(error_msg) from e


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
        Iterator of ModuleVarSpec objects
        
    Raises:
        TypeError: If the inputs are not of the expected types
        InvalidPythonFileError: If the file is not a valid Python file
        ModulePathError: If the path structure is invalid
        ModuleLoadError: If there's an issue loading modules
        SpecialFileError: If there's an issue processing special files
    """
    from pinjected.module_inspector import get_project_root
    
    # Type validation
    if not isinstance(file_path, Path):
        raise TypeError(f"file_path must be a Path object, got {type(file_path)}")
    
    if not isinstance(attr_name, str):
        raise TypeError(f"attr_name must be a string, got {type(attr_name)}")
    
    if not attr_name:
        raise ValueError("attr_name cannot be empty")
    
    # Normalize parameters
    try:
        special_filenames_list = normalize_special_filenames(special_filenames)
    except TypeError as e:
        logger.error(f"Failed to normalize special_filenames: {e}")
        raise
    
    # Handle root_module_path detection
    if root_module_path is None:
        try:
            root_path_str = get_project_root(str(file_path))
            if not root_path_str:
                raise ModulePathError(f"Could not determine project root for {file_path}")
            root_module_path = Path(root_path_str)
        except Exception as e:
            error_msg = f"Failed to determine root module path: {e}"
            logger.error(error_msg)
            raise ModulePathError(error_msg) from e
    
    # Ensure we have absolute paths
    file_path = file_path.absolute()
    root_module_path = root_module_path.absolute()
    
    # Validate file path is a Python file
    try:
        validate_python_file_path(file_path)
    except (TypeError, InvalidPythonFileError) as e:
        logger.error(f"Invalid Python file path: {e}")
        raise
    
    logger.trace(f"Project root path: {root_module_path}")
    
    # Validate file path is under root module path
    if not str(file_path).startswith(str(root_module_path)):
        error_msg = f"File path {file_path} is not under root module path {root_module_path}"
        logger.error(error_msg)
        raise ModulePathError(error_msg)
    
    # Build module hierarchy from root to target
    try:
        module_hierarchy = build_module_hierarchy(file_path, root_module_path)
        logger.debug(f"Built module hierarchy with {len(module_hierarchy.module_paths)} paths")
    except (TypeError, InvalidPythonFileError, ModulePathError) as e:
        error_msg = f"Failed to build module hierarchy: {e}"
        logger.error(error_msg)
        raise ModulePathError(error_msg) from e
    
    # Process the module hierarchy
    has_yielded_results = False
    
    # Check for special files at the root level first
    try:
        logger.debug(f"Processing root directory: {root_module_path}")
        root_results = list(process_directory(
            directory=root_module_path,
            root_module_path=root_module_path,
            attr_name=attr_name,
            special_filenames=special_filenames_list
        ))
        
        if root_results:
            has_yielded_results = True
            for result in root_results:
                yield result
    except (TypeError, SpecialFileError) as e:
        error_msg = f"Error processing root directory: {e}"
        logger.error(error_msg)
        raise SpecialFileError(error_msg) from e
    
    # Process each module in the path, from root to target
    for module_path in module_hierarchy.module_paths:
        logger.debug(f"Processing module path: {module_path}")
        
        # Get module name
        try:
            module_name = get_module_name(module_path, root_module_path)
        except (TypeError, InvalidPythonFileError, ModulePathError) as e:
            error_msg = f"Error getting module name for {module_path}: {e}"
            logger.error(error_msg)
            raise ModulePathError(error_msg) from e
        
        # Import the module
        try:
            module = load_module_from_path(module_name, module_path)
        except (TypeError, InvalidPythonFileError, ModuleLoadError) as e:
            error_msg = f"Error loading module {module_name} from {module_path}: {e}"
            logger.error(error_msg)
            raise ModuleLoadError(error_msg) from e
        
        # Check for attribute in the current module
        try:
            attr_spec = extract_module_attribute(module, module_name, attr_name)
            if attr_spec:
                logger.debug(f"Found attribute {attr_name} in module {module_name}")
                has_yielded_results = True
                yield attr_spec
        except (TypeError, ModuleAttributeError) as e:
            error_msg = f"Error extracting attribute {attr_name} from module {module_name}: {e}"
            logger.error(error_msg)
            raise ModuleAttributeError(error_msg) from e
        
        # Process special files in the current module's directory
        parent_dir = module_path.parent
        logger.debug(f"Processing directory: {parent_dir}")
        
        try:
            directory_results = list(process_directory(
                directory=parent_dir,
                root_module_path=root_module_path,
                attr_name=attr_name,
                special_filenames=special_filenames_list,
                exclude_path=module_path  # Don't process the module file itself again
            ))
            
            if directory_results:
                has_yielded_results = True
                for result in directory_results:
                    yield result
        except (TypeError, SpecialFileError) as e:
            error_msg = f"Error processing directory {parent_dir}: {e}"
            logger.error(error_msg)
            raise SpecialFileError(error_msg) from e
    
    if not has_yielded_results:
        logger.info(f"No attributes named '{attr_name}' found in any module or special file")