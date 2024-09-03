from pathlib import Path
from pprint import pprint

from pinjected.helper_structure import MetaContext
from pinjected.module_helper import walk_module_attr
from pinjected.module_inspector import get_project_root


def test_get_project_root():
    # this is a host dependent test...
    root = get_project_root(
        "/Users/s22625/repos/archpainter/archpainter/style_transfer/iccv_artifacts.py",
    )
    assert root == "/Users/s22625/repos/archpainter"


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
