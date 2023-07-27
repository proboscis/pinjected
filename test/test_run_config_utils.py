from pathlib import Path

from pinject_design import Injected
from pinject_design.di.util import instances
from pinject_design.run_config_utils import create_idea_configurations, run_injected
from pinject_design.helpers import find_module_attr

TEST_MODULE=Path("../pinject_design/test_package/child/module1.py")

def test_create_configurations():
    create_idea_configurations(
        TEST_MODULE.expanduser(),
        default_design_path="dummy_path"
    )


test_design = instances(x=0)
test_var = Injected.by_name("x")


def test_run_injected():
    res = run_injected(
        "get",
        "pinject_design.test_package.child.module1.test_runnable",
        "pinject_design.test_package.child.module1.design01",
        return_result=True
    )
    print(res)
    assert res=="hello world"

