from pathlib import Path

from pinject_design.module_inspector import get_project_root
from pinject_design.run_config_utils import walk_module_attr


def test_get_project_root():
    root = get_project_root(
        "/Users/s22625/repos/archpainter/archpainter/style_transfer/iccv_artifacts.py",
    )
    assert root == "/Users/s22625/repos/archpainter"


def test_walk_module_attr():
    test_file = "/Users/s22625/repos/pinject-design/pinject_design/test_package/child/module1.py"
    for item in walk_module_attr(Path(test_file),"__meta_design__"):
        print(item)

