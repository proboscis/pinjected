"""Utility for loading modules and variables from module paths."""
import importlib
from typing import Any


def load_module_var(module_path: str) -> Any:
    """
    Load a variable from a module path.
    
    Args:
        module_path: The module path in the format "module.submodule.variable"
        
    Returns:
        The variable from the module
        
    Raises:
        ImportError: If the module cannot be imported
        AttributeError: If the variable cannot be found in the module
    """
    parts = module_path.split(".")
    
    if len(parts) < 2:
        raise ValueError(f"Invalid module path: {module_path}. Expected format: module.submodule.variable")
    
    var_name = parts[-1]
    module_name = ".".join(parts[:-1])
    
    try:
        module = importlib.import_module(module_name)
        return getattr(module, var_name)
    except ImportError as e:
        raise ImportError(f"Failed to import module {module_name}: {str(e)}")
    except AttributeError as e:
        raise AttributeError(f"Failed to find variable {var_name} in module {module_name}: {str(e)}")
