from pathlib import Path
from pprint import pprint

from pinjected.helper_structure import MetaContext
from pinjected.module_inspector import get_project_root
from pinjected.run_config_utils import create_idea_configurations
from pinjected.helpers import walk_module_attr, gather_meta_context


def test_get_project_root():
    # this is a host dependent test...
    root = get_project_root(
        "/Users/s22625/repos/archpainter/archpainter/style_transfer/iccv_artifacts.py",
    )
    assert root == "/Users/s22625/repos/archpainter"


def test_walk_module_attr():
    test_file = "/Users/s22625/repos/pinject-design/pinject_design/test_package/child/module1.py"
    items = []
    for item in walk_module_attr(Path(test_file), "__meta_design__"):
        items.append(item)
    pprint(items)


def test_gather_meta_design():
    test_file = "/Users/s22625/repos/pinject-design/pinject_design/test_package/child/module1.py"
    mc:MetaContext = gather_meta_context(Path(test_file))
    print(mc.accumulated.provide('name'))


def test_config_creator():
    test_file = "/Users/s22625/repos/pinject-design/pinject_design/test_package/child/module1.py"
    confs = create_idea_configurations(
        module_path=test_file,
        print_to_stdout=False
    )
    pprint(confs)
