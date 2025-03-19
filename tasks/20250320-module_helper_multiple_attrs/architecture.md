# Module Helper Enhancement: Multiple Attribute Support

## Overview

This enhancement updates the `walk_module_with_special_files` function and related functionality in `module_helper.py` to support multiple attribute names. This allows the caller to search for multiple attributes in a single pass through the module hierarchy, with results yielded in the order specified by the caller.

## Core Changes

1. Update `DirectoryProcessParams` to use a list of attribute names instead of a single attribute name
2. Modify `process_special_file` to accept multiple attribute names and return a dictionary mapping names to their found attributes
3. Update `process_directory` to handle the dictionary return type from `process_special_file`
4. Revise `walk_parent_modules` and related functions to support multiple attribute names
5. Update `validate_attr_params` to normalize and validate attribute names (string or list)
6. Enhance `walk_module_with_special_files` to support the new multi-attribute functionality

## Interface Changes

### DirectoryProcessParams

```python
@dataclass(frozen=True)
class DirectoryProcessParams:
    """
    Parameters for processing a directory looking for special files.
    """
    directory: Path
    root_module_path: Path
    attr_names: List[str]  # Changed from attr_name: str
    special_filenames: List[str]
    exclude_path: Optional[Path] = None
```

### process_special_file

```python
def process_special_file(
    special_file_path: Path,
    root_module_path: Path,
    attr_names: List[str]
) -> dict[str, ModuleVarSpec]:
    """
    Process a special file and extract the attributes if they exist.
    
    Returns:
        A dictionary mapping attribute names to their ModuleVarSpec objects
        (only includes attributes that were found)
    """
```

### walk_module_with_special_files

```python
def walk_module_with_special_files(
    file_path: Path, 
    attr_names: Union[str, List[str]], 
    special_filenames: Optional[Union[str, List[str]]] = ["__pinjected__.py"], 
    root_module_path: Optional[Path] = None
) -> Iterator[ModuleVarSpec]:
    """
    Walk from the root module down to the target file_path, looking for the 
    specified attributes in each module along the path.
    
    Args:
        file_path: Path to the module file to start searching from
        attr_names: Single attribute name or list of attribute names to look for
        special_filenames: List of filenames to look for in each directory
        root_module_path: The root module path to use (if None, it will be detected)
        
    Returns:
        Iterator of ModuleVarSpec objects, yielding results in the same order as attr_names
    """
```

### validate_attr_params

```python
def validate_attr_params(
    file_path: Path, 
    attr_names: Union[str, List[str]]
) -> List[str]:
    """
    Validate common parameters for attribute search functions and normalize attr_names.
    
    Returns:
        Normalized list of attribute names
    """
```

## Ordering Behavior

The key requirement is that attributes are yielded in the same order as specified in the `attr_names` parameter:

1. For each module, attributes will be yielded in the exact order specified in `attr_names`
2. This ordering is maintained consistently across all modules in the hierarchy
3. The function still traverses from top-level modules to deeper modules
4. Backward compatibility is maintained by accepting a single string attribute name