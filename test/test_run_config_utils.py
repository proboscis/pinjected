import sys
from pathlib import Path

import pinjected
from pinjected import *
from pinjected.di.util import instances
from pinjected.helper_structure import MetaContext
from pinjected.ide_supports.create_configs import create_idea_configurations
from pinjected.run_helpers.run_injected import run_injected
from pinjected.pinjected_logging import logger

from pinjected.v2.async_resolver import AsyncResolver

p_root = Path(__file__).parent.parent
TEST_MODULE = p_root/"pinjected/test_package/child/module1.py"
import pytest


@pytest.mark.asyncio
async def test_create_configurations():
    from pinjected.ide_supports.default_design import pinjected_internal_design
    configs = create_idea_configurations()
    mc = await MetaContext.a_gather_from_path(p_root/"pinjected/ide_supports/create_configs.py")
    dd = (await mc.a_final_design) + design(
        module_path=TEST_MODULE,
        interpreter_path=sys.executable,
    ) + pinjected_internal_design
    rr = AsyncResolver(dd)
    res = await rr[configs]
    print(res)


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
