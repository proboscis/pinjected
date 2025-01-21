from pathlib import Path
from pprint import pprint

from pinjected.helper_structure import MetaContext
from pinjected.module_helper import walk_module_attr
from pinjected.module_inspector import get_project_root


def test_get_project_root():
    # Use relative path from test directory
    test_file = Path(__file__).parent / "test_package/child/module1.py"
    root = get_project_root(str(test_file))
    assert root == str(Path(__file__).parent)


def test_walk_module_attr():
    test_file = Path(__file__).parent / "test_package/child/module1.py"
    items = []
    for item in walk_module_attr(test_file, "__meta_design__"):
        items.append(item)
    pprint(items)


def test_gather_meta_design():
    test_file = Path(__file__).parent / "test_package/child/module1.py"
    mc: MetaContext = MetaContext.gather_from_path(test_file)
    assert mc.final_design.provide('name') == "test_package.child.module1"
