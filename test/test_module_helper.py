import importlib
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


def test_no_duplicates():
    """Test that walk_module_with_special_files doesn't yield duplicate attributes."""
    test_file = Path(__file__).parent / "test_package/child/module1.py"
    root_module_path = Path(__file__).parent
    
    # Include all special files
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
    
    # Extract the paths
    paths = [item.var_path for item in items]
    
    # Check for duplicates
    unique_paths = set(paths)
    
    # If there are duplicates, paths and unique_paths will have different lengths
    assert len(paths) == len(unique_paths), f"Found duplicate attributes: {len(paths) - len(unique_paths)} duplicates"
    
    # More detailed error message if duplicates are found
    if len(paths) != len(unique_paths):
        duplicate_counts = {}
        for path in paths:
            if path in duplicate_counts:
                duplicate_counts[path] += 1
            else:
                duplicate_counts[path] = 1
        
        # Print duplicates
        print("Duplicate attributes found:")
        for path, count in duplicate_counts.items():
            if count > 1:
                print(f"  - {path}: {count} occurrences")


def test_multiple_attr_names_order():
    """Test that walk_module_with_special_files yields attributes in the specified order."""
    test_file = Path(__file__).parent / "test_package/child/module1.py"
    root_module_path = Path(__file__).parent
    
    # Test with multiple attribute names
    attr_names = ["__meta_design__", "special_config"]
    items = list(walk_module_with_special_files(
        test_file, 
        attr_names, 
        ["__pinjected__.py", "config.py", "__init__.py"],
        root_module_path=root_module_path
    ))
    
    # Print items for debugging
    print(f"Found {len(items)} items:")
    for i, item in enumerate(items):
        print(f"  {i}. {item.var_path}")
    
    # Group items by their attribute name
    meta_design_items = [item for item in items if "__meta_design__" in item.var_path]
    special_config_items = [item for item in items if "special_config" in item.var_path]
    
    # Check that we found both attribute types
    assert len(meta_design_items) > 0, "Should find __meta_design__ attributes"
    assert len(special_config_items) > 0, "Should find special_config attributes"
    
    # Check ordering by attribute name
    # In each directory, __meta_design__ items should come before special_config items
    for i, item in enumerate(items):
        # Find first special_config in same directory
        if "__meta_design__" in item.var_path:
            module_path = item.var_path.split(".__meta_design__")[0]
            for j in range(i + 1, len(items)):
                compare_item = items[j]
                compare_module = compare_item.var_path.split(".")[0]
                # If in same module and it's a special_config, we're following the right order
                if module_path == compare_module and "special_config" in compare_item.var_path:
                    # This is correct ordering (meta_design then special_config)
                    break
            # If we found a special_config before __meta_design__ in the same module, that's wrong
            for j in range(0, i):
                compare_item = items[j]
                compare_module = compare_item.var_path.split(".")[0]
                if module_path == compare_module and "special_config" in compare_item.var_path:
                    assert False, f"Incorrect order: {compare_item.var_path} came before {item.var_path}"


def test_multiple_attr_names_complex_order():
    """Test that walk_module_with_special_files yields attributes with more than 2 attr names in the correct order."""
    test_file = Path(__file__).parent / "test_package/child/module1.py"
    root_module_path = Path(__file__).parent
    
    # Define a non-standard order to verify ordering is respected
    # This order is different from the typical order they would be found in files
    attr_names = ["special_config", "test_test_object", "__meta_design__"]
    
    items = list(walk_module_with_special_files(
        test_file, 
        attr_names, 
        ["__pinjected__.py", "config.py", "__init__.py"],
        root_module_path=root_module_path
    ))
    
    # Print items for debugging
    print(f"Found {len(items)} items:")
    for i, item in enumerate(items):
        print(f"  {i}. {item.var_path}")
    
    # Extract each item's attribute type for global ordering check
    attr_types = []
    for item in items:
        if "special_config" in item.var_path:
            attr_types.append("special_config")
        elif "test_test_object" in item.var_path:
            attr_types.append("test_test_object")
        elif "__meta_design__" in item.var_path:
            attr_types.append("__meta_design__")
    
    # Group items by module
    modules = {}
    for item in items:
        if "special_config" in item.var_path:
            module_path = item.var_path.split(".special_config")[0]
            attr_type = "special_config"
        elif "test_test_object" in item.var_path:
            module_path = item.var_path.split(".test_test_object")[0]
            attr_type = "test_test_object"
        elif "__meta_design__" in item.var_path:
            module_path = item.var_path.split(".__meta_design__")[0]
            attr_type = "__meta_design__"
        else:
            continue
            
        if module_path not in modules:
            modules[module_path] = []
        modules[module_path].append((attr_type, item))
    
    # Check ordering within each module
    found_multiple_attrs = False
    for module_path, attrs in modules.items():
        if len(attrs) > 1:
            found_multiple_attrs = True
            
            # Check that attributes appear in the same order as attr_names
            module_attr_order = [attr[0] for attr in attrs]
            print(f"Module {module_path} attributes in order: {module_attr_order}")
            
            # Get expected order of attributes actually found in this module
            expected_order = [attr for attr in attr_names if attr in module_attr_order]
            assert module_attr_order == expected_order, \
                f"Attributes for module {module_path} not in correct order. Expected {expected_order}, got {module_attr_order}"
    
    # Make sure we found at least one module with multiple attributes
    assert found_multiple_attrs, "No modules with multiple attributes found to test ordering"
    
    # Check strict global ordering across modules too
    # For all "special_config" attributes, they should all come before any "test_test_object" attributes,
    # which should all come before any "__meta_design__" attributes
    last_attr_index = {}
    for i, attr_type in enumerate(attr_types):
        if attr_type not in last_attr_index:
            last_attr_index[attr_type] = i
        else:
            last_attr_index[attr_type] = i
    
    # Verify attribute ordering consistency across all modules
    for i, attr in enumerate(attr_names):
        if attr in last_attr_index:
            for j, earlier_attr in enumerate(attr_names[:i]):
                if earlier_attr in last_attr_index:
                    assert last_attr_index[earlier_attr] < last_attr_index[attr], \
                        f"Global attribute ordering violation: last {earlier_attr} (position {last_attr_index[earlier_attr]}) " \
                        f"came after first {attr} (position {last_attr_index[attr]})"
    
    # Try a different ordering to ensure it's respected
    reverse_attr_names = list(reversed(attr_names))
    reverse_items = list(walk_module_with_special_files(
        test_file, 
        reverse_attr_names, 
        ["__pinjected__.py", "config.py", "__init__.py"],
        root_module_path=root_module_path
    ))
    
    # Extract types for the reverse order
    reverse_attr_types = []
    for item in reverse_items:
        if "special_config" in item.var_path:
            reverse_attr_types.append("special_config")
        elif "test_test_object" in item.var_path:
            reverse_attr_types.append("test_test_object")
        elif "__meta_design__" in item.var_path:
            reverse_attr_types.append("__meta_design__")
    
    # Verify we got a different order with the reversed input
    if "special_config" in reverse_attr_types and "__meta_design__" in reverse_attr_types:
        # Find index of first occurrence of each
        first_special_config = reverse_attr_types.index("special_config") if "special_config" in reverse_attr_types else -1
        first_meta_design = reverse_attr_types.index("__meta_design__") if "__meta_design__" in reverse_attr_types else -1
        
        if first_special_config != -1 and first_meta_design != -1:
            # In the reversed order, __meta_design__ should come before special_config
            assert first_meta_design < first_special_config, \
                "Reversed order not respected. __meta_design__ should come before special_config"