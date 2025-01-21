from pathlib import Path
from pprint import pprint

from pinjected.helper_structure import MetaContext
from pinjected.module_helper import walk_module_attr
from pinjected.module_inspector import get_project_root


def test_get_project_root(tmp_path):
    # Create a test project structure
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()
    (project_dir / "__init__.py").touch()

    # Create a nested directory structure
    sub_dir = project_dir / "subdir" / "nested"
    sub_dir.mkdir(parents=True)
    test_file = sub_dir / "test_file.py"
    test_file.touch()

    # Test that get_project_root correctly finds the root
    root = get_project_root(str(test_file))
    assert root == str(project_dir)


def test_walk_module_attr():
    test_file = "/Users/s22625/repos/pinject-design/pinjected/test_package/child/module1.py"
    items = []
    for item in walk_module_attr(Path(test_file), "__meta_design__"):
        items.append(item)
    pprint(items)


def test_gather_meta_design():
    test_file = "/Users/s22625/repos/pinject-design/pinjected/test_package/child/module1.py"
    mc: MetaContext = MetaContext.gather_from_path(Path(test_file))
    mc.final_design.provide('name') == "test_package.child.module1"
