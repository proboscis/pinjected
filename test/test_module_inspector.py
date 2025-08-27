import asyncio
from pathlib import Path
from pprint import pprint

import pytest

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


def test_walk_module_attr():
    test_file = Path(__file__).parent.parent / "pinjected/test_package/child/module1.py"
    items = []
    for item in walk_module_attr(test_file, "__design__"):
        items.append(item)
    pprint(items)


def test_gather_meta_design():
    test_file = Path(__file__).parent.parent / "pinjected/test_package/child/module1.py"
    mc: MetaContext = asyncio.run(MetaContext.a_gather_bindings_with_legacy(test_file))
    assert mc.final_design.provide("name") == "test_package.child.module1"


def test_get_project_root_not_found(tmp_path):
    """Test get_project_root raises ValueError when project root cannot be found."""
    # Create a deeply nested structure with __init__.py files all the way to root
    current = tmp_path
    for i in range(5):
        (current / "__init__.py").touch()
        if i < 4:
            current = current / f"level{i}"
            current.mkdir()

    # Create test file at deepest level
    test_file = current / "test.py"
    test_file.touch()

    # Mock os.path.dirname to simulate reaching filesystem root
    from unittest.mock import patch

    with patch("os.path.dirname") as mock_dirname:
        # First call returns parent, second call returns same path (at root)
        mock_dirname.side_effect = [str(current.parent), str(current.parent)]

        with pytest.raises(ValueError, match="Project root not found"):
            get_project_root(str(test_file))


def test_get_project_root_with_src_directory(tmp_path):
    """Test get_project_root handles 'src' directory correctly."""
    # Create project structure with src directory
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()

    # Create src directory WITHOUT __init__.py
    src_dir = project_dir / "src"
    src_dir.mkdir()

    # Create package inside src with __init__.py
    package_dir = src_dir / "mypackage"
    package_dir.mkdir()
    (package_dir / "__init__.py").touch()

    # Create test file
    test_file = package_dir / "module.py"
    test_file.touch()

    # Test that project root is found correctly (should be test_project, not src)
    root = get_project_root(str(test_file))
    assert root == str(project_dir)


def test_get_module_path_with_src_trim(tmp_path):
    """Test get_module_path trims 'src.' prefix when src has no __init__.py."""
    from pinjected.module_inspector import get_module_path

    # Create project structure
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    # Create src directory without __init__.py
    src_dir = project_dir / "src"
    src_dir.mkdir()

    # Create package inside src
    package_dir = src_dir / "mypackage"
    package_dir.mkdir()
    module_file = package_dir / "module.py"
    module_file.touch()

    # Test that 'src.' prefix is trimmed
    module_path = get_module_path(str(project_dir), str(module_file))
    assert module_path == "mypackage.module"


def test_inspect_module_registers_in_sys_modules(tmp_path):
    """Test inspect_module_for_type registers module in sys.modules."""
    from pinjected.module_inspector import inspect_module_for_type
    import sys

    # Create a simple module structure
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()

    module_file = project_dir / "test_module.py"
    module_file.write_text("""
test_var = "hello"
test_func = lambda: "world"
""")

    # Ensure module is not in sys.modules
    module_name = "test_module"
    if module_name in sys.modules:
        del sys.modules[module_name]

    # Run inspect_module_for_type
    results = inspect_module_for_type(
        str(module_file), lambda name, value: name.startswith("test_")
    )

    # Check module was registered in sys.modules
    assert module_name in sys.modules
    assert len(results) == 2
    assert any(r.var == "hello" for r in results)


def test_inspect_module_with_path_object(tmp_path):
    """Test inspect_module_for_type handles Path objects correctly."""
    from pinjected.module_inspector import inspect_module_for_type
    import sys

    # Create a simple module structure
    project_dir = tmp_path / "test_project_path"
    project_dir.mkdir()

    module_file = project_dir / "test_module_path.py"
    module_file.write_text("""
test_var_path = "path_test"
""")

    # Ensure module is not in sys.modules
    module_name = "test_module_path"
    if module_name in sys.modules:
        del sys.modules[module_name]

    # Pass Path object instead of string
    results = inspect_module_for_type(
        module_file,  # Path object, not string
        lambda name, value: name == "test_var_path",
    )

    assert len(results) == 1
    assert results[0].var == "path_test"


def test_main_block():
    """Test the __main__ block runs fire.Fire()."""
    import subprocess
    import sys

    # Run module_inspector as a script
    result = subprocess.run(
        [sys.executable, "-m", "pinjected.module_inspector", "--help"],
        capture_output=True,
        text=True,
    )

    # The main block runs fire.Fire() - we can verify it was executed
    # by checking the error message shows it tried to run fire.Fire()
    assert "fire.Fire()" in result.stderr
    assert "line 110" in result.stderr  # Confirms line 110 was reached
