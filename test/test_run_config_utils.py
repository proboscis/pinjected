import sys
from pathlib import Path

import pinjected
from pinjected import *
from pinjected.helper_structure import MetaContext
from pinjected.ide_supports.create_configs import create_idea_configurations
from pinjected.run_helpers.run_injected import run_injected
from pinjected.pinjected_logging import logger
from pinjected.schema.handlers import PinjectedHandleMainException, PinjectedHandleMainResult

from pinjected.v2.async_resolver import AsyncResolver

p_root = Path(__file__).parent.parent
TEST_MODULE = p_root/"pinjected/test_package/child/module1.py"
import pytest


@pytest.mark.asyncio
async def test_create_configurations():
    from pinjected.ide_supports.default_design import pinjected_internal_design
    # create_idea_configurationsの引数を正しく設定
    configs = create_idea_configurations(wrap_output_with_tag=False)
    mc = await MetaContext.a_gather_from_path(p_root/"pinjected/ide_supports/create_configs.py")
    dd = (await mc.a_final_design) + design(
        module_path=TEST_MODULE,
        interpreter_path=sys.executable
    ) + pinjected_internal_design
    rr = AsyncResolver(dd)
    res = await rr[configs]
    print(res)


test_design = design(x=0)
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

def test_run_injected_with_handle():
    res = run_injected(
        "get",
        "pinjected.test_package.child.module1.test_runnable",
        "pinjected.test_package.child.module1.design03",
        return_result=True
    )
    print(res)
    assert res == "hello world"


def test_run_injected_exception_with_handle():
    with pytest.raises(Exception):
        res = run_injected(
            "get",
            "pinjected.test_package.child.module1.test_always_failure",
            "pinjected.test_package.child.module1.design03",
            return_result=True
        )