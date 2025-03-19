# Module Helper Architecture

## Overview

The `module_helper.py` provides utilities for Python module navigation, loading, and attribute extraction. It enables walking through module hierarchies to find specific attributes in modules and special files.

## Core Concepts

1. **Module Navigation**: Traversing a directory structure to find Python modules
2. **Module Loading**: Loading Python modules from file paths
3. **Attribute Extraction**: Finding specific attributes in loaded modules
4. **Special Files**: Processing specific files (like `__pinjected__.py`) in a directory structure

## Data Structures

### Exception Classes

```python
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
```

### Dataclasses

```python
@dataclass(frozen=True)
class DirectoryProcessParams:
    """
    Parameters for processing a directory looking for special files.
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
    """
    root_module_path: Path
    module_paths: List[Path]
```

## Function Interfaces

### Validation Functions

```python
def validate_python_file_path(file_path: Path) -> None:
    """Validates if a path is a valid Python file."""
    
def validate_directory_path(directory: Path) -> None:
    """Validates if a path is a valid directory."""
    
def validate_path_under_root(file_path: Path, root_path: Path) -> None:
    """Validates if a file path is under a root path."""
    
def validate_module_paths(file_path: Path, root_module_path: Path) -> None:
    """Validates the module paths are valid."""
```

### Path Processing Functions

```python
def normalize_special_filenames(
    special_filenames: Optional[Union[str, List[str]]]
) -> List[str]:
    """Normalize the special_filenames parameter to ensure it's a list."""
    
def get_relative_path(file_path: Path, root_module_path: Path) -> Path:
    """Gets the relative path from root_module_path to file_path."""
    
def get_module_name(file_path: Path, root_module_path: Path) -> str:
    """Determine the module name from a file path relative to the root module path."""
    
def prepare_module_paths(
    file_path: Path,
    root_module_path: Optional[Path]
) -> Tuple[Path, Path]:
    """Prepare and validate the module paths."""
```

### Module Operations Functions

```python
def create_module_spec(module_name: str, file_path: Path) -> Tuple[ModuleType, importlib.machinery.ModuleSpec]:
    """Creates a module spec from a file path."""
    
def load_module_from_path(module_name: str, file_path: Path) -> ModuleType:
    """Load a module from a file path."""
    
def extract_module_attribute(
    module: ModuleType, 
    module_name: str, 
    attr_name: str
) -> Optional[ModuleVarSpec]:
    """Extract an attribute from a module if it exists."""
    
def process_parent_module(
    parent_file_path: Path,
    attr_name: str,
    root_module_path: Path
) -> Optional[ModuleVarSpec]:
    """Process a parent module to extract attributes."""
```

### Module Traversal Functions

```python
def build_parent_path_tree(
    current_path: Path, 
    root_module_path: Path
) -> List[Path]:
    """Build a tree of parent paths with __init__.py files."""
    
def build_module_hierarchy(
    file_path: Path,
    root_module_path: Path
) -> ModuleHierarchy:
    """Build a hierarchy of modules from root to target file path."""
    
def walk_parent_modules(
    file_path: Path, 
    attr_name: str, 
    root_module_path: Path
) -> Iterator[ModuleVarSpec]:
    """Walk from current file's parent directory to root, looking for attributes."""
```

### Special File Functions

```python
def find_special_files(
    directory: Path,
    special_filenames: List[str],
    exclude_path: Optional[Path] = None
) -> List[Path]:
    """Find all special files in a directory."""
    
def process_special_file(
    special_file_path: Path,
    root_module_path: Path,
    attr_name: str
) -> Optional[ModuleVarSpec]:
    """Process a special file and extract the attribute if it exists."""
    
def process_directory(
    params: DirectoryProcessParams
) -> Iterator[ModuleVarSpec]:
    """Process a directory for special files and extract attributes."""
```

### High-Level API Functions

```python
def process_module_hierarchy(
    module_hierarchy: ModuleHierarchy,
    attr_name: str,
    special_filenames: List[str]
) -> Iterator[ModuleVarSpec]:
    """Process a module hierarchy to find attributes in modules and special files."""
    
def walk_module_attr(
    file_path: Path, 
    attr_name: str, 
    root_module_path: Optional[Path] = None
) -> Iterator[ModuleVarSpec]:
    """Walk from a root module to the file_path, looking for attributes."""
    
def walk_module_with_special_files(
    file_path: Path, 
    attr_name: str, 
    special_filenames: Optional[Union[str, List[str]]] = ["__pinjected__.py"], 
    root_module_path: Optional[Path] = None
) -> Iterator[ModuleVarSpec]:
    """
    Walk from the root module down to the target file_path, looking for the 
    specified attribute in each module along the path.
    """
```

## Control Flow

1. The main entry point is `walk_module_with_special_files` which performs the following steps:
   - Validate and normalize input parameters
   - Build a module hierarchy from root to target
   - Process special files in the root directory
   - Process each module in the hierarchy, looking for the attribute
   - Yield found attributes as `ModuleVarSpec` objects

2. The `process_module_hierarchy` function:
   - Processes each module in the hierarchy from root to target
   - Extracts attributes from each module
   - Processes special files in each module's directory

3. The `process_directory` function:
   - Finds special files in a directory
   - Processes each special file to extract attributes
   - Yields found attributes

## Error Handling

- Each function has well-defined error conditions and raises specific exceptions
- Exceptions are properly propagated to the caller
- Validation functions ensure proper inputs before processing