from pathlib import Path
from pprint import pprint

from pinjected.helper_structure import MetaContext
from pinjected.module_helper import walk_module_attr
from pinjected.module_inspector import get_project_root


def test_get_project_root(tmp_path):
    """Test get_project_root with a typical Python project structure.
    
    Project structure:
    test_project/          # Project root (no __init__.py)
    └── package/          # Package root
        ├── __init__.py   # Makes it a Python package
        └── module.py     # Test file
    """
    # Create project root (without __init__.py)
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()
    
    # Create package directory with __init__.py
    package_dir = project_dir / "package"
    package_dir.mkdir()
    (package_dir / "__init__.py").touch()
    
    # Create a module file
    test_file = package_dir / "module.py"
    test_file.touch()

    # Test that get_project_root correctly finds the project root
    # (the directory above the one containing __init__.py)
    root = get_project_root(str(test_file))
    assert root == str(project_dir)


import pytest

def test_walk_module_attr():
    test_file = Path(__file__).parent.parent / "pinjected/test_package/child/module1.py"
    items = []
    for item in walk_module_attr(test_file, "__meta_design__"):
        items.append(item)
    pprint(items)


def test_gather_meta_design():
    test_file = Path(__file__).parent.parent / "pinjected/test_package/child/module1.py"
    mc: MetaContext = MetaContext.gather_from_path(test_file)
    assert mc.final_design.provide('name') == "test_package.child.module1"
