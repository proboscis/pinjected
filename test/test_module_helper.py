from pathlib import Path
from pprint import pprint

import pytest

from pinjected.module_helper import walk_module_attr, walk_module_with_special_files
from pinjected.module_inspector import get_project_root


def test_walk_module_with_special_files_single_file():
    """Test walk_module_with_special_files with a single special file."""
    # Set up test paths
    test_file = Path(__file__).parent / "test_package/child/module1.py"
    root_module_path = Path(__file__).parent
    
    # Test with default (looking for __pinjected__.py)
    items = list(walk_module_with_special_files(
        test_file, 
        "__meta_design__", 
        ["__pinjected__.py", "__init__.py"],
        root_module_path=root_module_path
    ))
    
    # Print items for debugging
    print(f"Found {len(items)} items:")
    for item in items:
        print(f"  - {item.var_path}")
        
    # Check if we find the module's __meta_design__
    module_found = False
    for item in items:
        if "module1.__meta_design__" in item.var_path:
            module_found = True
            assert item.var.provide('name') == "test_package.child.module1"
            
    assert module_found, "Should find __meta_design__ from module1.py"
    
    # Check if we find the child __pinjected__'s __meta_design__
    pinjected_found = False
    for item in items:
        if "test_package.child.__pinjected__.__meta_design__" in item.var_path:
            pinjected_found = True
            assert item.var.provide('special_var') == "from_pinjected_file"
            
    assert pinjected_found, "Should find __meta_design__ from child/__pinjected__.py"


def test_walk_module_with_special_files_multiple_files():
    """Test walk_module_with_special_files with multiple special files."""
    test_file = Path(__file__).parent / "test_package/child/module1.py"
    root_module_path = Path(__file__).parent
    
    # Test with multiple special filenames
    special_files = ["__pinjected__.py", "config.py", "__init__.py"]
    items = list(walk_module_with_special_files(
        test_file, 
        "__meta_design__", 
        special_files, 
        root_module_path=root_module_path
    ))
    
    # Print items for debugging
    print(f"Found {len(items)} items:")
    for item in items:
        print(f"  - {item.var_path}")
    
    # Check for __meta_design__ from both special files
    pinjected_found = False
    config_found = False
    
    for item in items:
        if "test_package.child.__pinjected__.__meta_design__" in item.var_path:
            pinjected_found = True
            assert item.var.provide('special_var') == "from_pinjected_file"
        elif "config.__meta_design__" in item.var_path:
            config_found = True
            assert item.var.provide('special_var') == "from_config_file"
            
    assert pinjected_found, "Should find __meta_design__ from __pinjected__.py"
    assert config_found, "Should find __meta_design__ from config.py"


def test_walk_module_with_special_files_string_param():
    """Test walk_module_with_special_files with a string parameter."""
    test_file = Path(__file__).parent / "test_package/child/module1.py"
    root_module_path = Path(__file__).parent
    
    # Test with a string parameter (should be converted to a list)
    items = list(walk_module_with_special_files(
        test_file, 
        "special_config", 
        "config.py",  # Should be converted to ["config.py"]
        root_module_path=root_module_path
    ))
    
    # Print items for debugging
    print(f"Found {len(items)} items:")
    for item in items:
        print(f"  - {item.var_path}")
    
    # Check if we found the special_config from config.py
    config_found = False
    for item in items:
        if "config.special_config" in item.var_path:
            config_found = True
            assert item.var['source'] == "config.py"
            assert item.var['value'] == "config_value"
            
    assert config_found, "Should find special_config from config.py"


def test_walk_module_with_special_files_multiple_attrs():
    """Test walk_module_with_special_files finding multiple attributes."""
    test_file = Path(__file__).parent / "test_package/child/module1.py"
    root_module_path = Path(__file__).parent
    
    # Look for special_config in both special files
    items = list(walk_module_with_special_files(
        test_file, 
        "special_config", 
        ["__pinjected__.py", "config.py"],
        root_module_path=root_module_path
    ))
    
    # Print items for debugging
    print(f"Found {len(items)} items:")
    for item in items:
        print(f"  - {item.var_path}")
    
    # Both files should have special_config
    sources = set()
    for item in items:
        if "special_config" in item.var_path:
            sources.add(item.var['source'])
    
    assert "__pinjected__" in sources, "Should find special_config from __pinjected__.py"
    assert "config.py" in sources, "Should find special_config from config.py"


def test_without_init_file():
    """Test walk_module_with_special_files without including __init__.py."""
    test_file = Path(__file__).parent / "test_package/child/module1.py"
    root_module_path = Path(__file__).parent
    
    # Don't include __init__.py in special_filenames
    items = list(walk_module_with_special_files(
        test_file, 
        "__meta_design__", 
        ["__pinjected__.py", "config.py"],  # No __init__.py
        root_module_path=root_module_path
    ))
    
    # Print items for debugging
    print(f"Found {len(items)} items:")
    for item in items:
        print(f"  - {item.var_path}")
    
    # We should only find module1's __meta_design__ (current file) and the special files, 
    # but not from any __init__.py files
    init_found = False
    for item in items:
        if "__init__.__meta_design__" in item.var_path:
            init_found = True
            
    assert not init_found, "Should not find __meta_design__ from __init__.py files"


def test_yielding_order():
    """Test the yielding order from top module to target file."""
    test_file = Path(__file__).parent / "test_package/child/module1.py"
    root_module_path = Path(__file__).parent
    
    # Include all special files to check ordering
    items = list(walk_module_with_special_files(
        test_file, 
        "__meta_design__", 
        ["__pinjected__.py", "config.py", "__init__.py"],
        root_module_path=root_module_path
    ))
    
    # Print items for debugging
    print(f"Found {len(items)} items:")
    for i, item in enumerate(items):
        print(f"  {i}. {item.var_path}")
    
    # Extract the paths for easier ordering assertion
    paths = [item.var_path for item in items]
    
    # Define the expected progression - from top to bottom
    # We expect modules to be processed from root to target
    
    # Check ordering by module depth - root modules should come before deeper modules
    for i in range(len(paths) - 1):
        for j in range(i + 1, len(paths)):
            current_depth = paths[i].count('.')
            next_depth = paths[j].count('.')
            
            # Skip comparison if they're from the same directory level
            if '.'.join(paths[i].split('.')[:2]) != '.'.join(paths[j].split('.')[:2]):
                # Higher module should come before deeper module
                if current_depth > next_depth:
                    assert False, f"Order incorrect: {paths[i]} (depth {current_depth}) came before {paths[j]} (depth {next_depth})"
    
    # Ensure at least one item exists from each expected level
    top_level_found = False
    mid_level_found = False
    target_file_found = False
    
    for path in paths:
        if "test_package.__pinjected__" in path:
            top_level_found = True
        elif "test_package.child.__" in path:
            mid_level_found = True
        elif "test_package.child.module1" in path:
            target_file_found = True
    
    # We should have items from all levels
    assert top_level_found, "Missing items from top level"
    assert mid_level_found, "Missing items from middle level" 
    assert target_file_found, "Missing items from target file"