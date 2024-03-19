import sys
from pathlib import Path

from pinjected import Injected
from pinjected.di.util import instances
from pinjected.helper_structure import MetaContext
from pinjected.ide_supports.create_configs import create_idea_configurations
from pinjected.run_helpers.run_injected import run_injected
from loguru import logger
TEST_MODULE = Path("../pinjected/test_package/child/module1.py")


def test_create_configurations():
    configs = create_idea_configurations(
        TEST_MODULE.expanduser(),
        default_design_path="dummy_path"
    )
    logger.info(configs)
    mc = MetaContext.gather_from_path('../pinjected/ide_supports/create_configs.py')
    (mc.final_design + instances(
        # print_to_stdout=True,
        module_path=TEST_MODULE,
        interpreter_path=sys.executable,
        # meta_context = mc,
        # logger = logger,
        # runner_script_path= Path(__file__),
    )).provide(configs)


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
