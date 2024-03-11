from pathlib import Path

from pinjected import Injected
from pinjected.di.util import instances
from pinjected.ide_supports.create_configs import create_idea_configurations
from pinjected.run_helpers.run_injected import run_injected

TEST_MODULE = Path("../pinject_design/test_package/child/module1.py")


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
        "pinjected.test_package.child.module1.test_runnable",
        "pinjected.test_package.child.module1.design01",
        return_result=True
    )
    print(res)
    assert res == "hello world"
