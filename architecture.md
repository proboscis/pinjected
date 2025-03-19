# Module Helper Architecture

## Purpose
Define a robust architecture for walking through Python module hierarchies to find special files with specific attributes, addressing current violations of coding guidelines.

## Core Components

### Data Structures

```python
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

@dataclass(frozen=True)
class ModuleVarSpec:
    """
    Specification for a module variable.
    
    Attributes:
        var: The variable value
        var_path: The full path to the variable
    """
    var: Any
    var_path: str
```

### Module Path Utilities

```python
def validate_python_file_path(file_path: Path) -> Tuple[bool, Optional[str]]:
    """Validates if a path is a valid Python file."""
    
def get_module_name(file_path: Path, root_module_path: Path) -> str:
    """Determine the module name from a file path relative to the root module path."""
    
def build_module_hierarchy(file_path: Path, root_module_path: Path) -> ModuleHierarchy:
    """Build a hierarchy of modules from root to target file path."""
```

### Module Loading and Attribute Extraction

```python
def load_module_from_path(module_name: str, file_path: Path) -> ModuleType:
    """Load a module from a file path."""
    
def extract_module_attribute(module: ModuleType, module_name: str, attr_name: str) -> Optional[ModuleVarSpec]:
    """Extract an attribute from a module if it exists."""
```

### Special File Processing

```python
def normalize_special_filenames(special_filenames: Optional[Union[str, List[str]]]) -> List[str]:
    """Normalize the special_filenames parameter to ensure it's a list."""
    
def find_special_files(directory: Path, special_filenames: List[str], exclude_path: Optional[Path] = None) -> List[Path]:
    """Find all special files in a directory."""
    
def process_special_file(special_file_path: Path, root_module_path: Path, attr_name: str) -> Optional[ModuleVarSpec]:
    """Process a special file and extract the attribute if it exists."""
    
def process_directory(directory: Path, root_module_path: Path, attr_name: str, special_filenames: List[str], exclude_path: Optional[Path] = None) -> Iterator[ModuleVarSpec]:
    """Process a directory for special files and extract attributes."""
```

### Main Function

```python
def walk_module_with_special_files(file_path: Path, attr_name: str, special_filenames: Optional[Union[str, List[str]]] = ["__pinjected__.py"], root_module_path: Optional[Path] = None) -> Iterator[ModuleVarSpec]:
    """
    Walk from the root module down to the target file_path, looking for the 
    specified attribute in each module along the path.
    """
```

## Error Handling Strategy

1. Each function will have explicit error handling that follows the guidelines:
   - No empty exception handlers
   - No exception blocks with only logging
   - Always re-raise exceptions with context when caught
   - No silent returns from exception blocks

2. Clear error messages will be provided with each exception
3. Custom exceptions will be used where appropriate
4. No default values will be returned on error conditions unless explicitly required

## Function Composition Flow

1. Input validation
2. Normalization of parameters 
3. Root module path determination
4. Module hierarchy building
5. Processing root directory for special files
6. Processing each module in the hierarchy
7. Yielding found attributes in proper order

## Guidelines Compliance
All functions will adhere to:
- Single responsibility principle
- Pure function design where possible
- Proper error propagation
- Clear naming conventions
- Appropriate logging
- No use of continue statements
- No deeply nested control structures