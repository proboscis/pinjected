"""
Here i test the functionality of testing module in pinjected.
1.
"""
from pathlib import Path
from pprint import pformat

import pytest

from pinjected import *
from tqdm import tqdm
from pinjected.pinjected_logging import logger

from pinjected.ide_supports.default_design import pinjected_internal_design
from pinjected.test_helper.test_aggregator import meta_design_acceptor, \
    Annotation, PinjectedTestAggregator, find_pinjected_annotations, VariableInFile
from pinjected.test_helper.test_runner import a_pinjected_run_all_test, a_pinjected_run_test, PinjectedTestResult, \
    a_visualize_test_results
from pinjected.v2.async_resolver import AsyncResolver

P_ROOT = Path(__file__).parent.parent
d = AsyncResolver(pinjected_internal_design)


# def test_find_target_variables():
#     path = P_ROOT / "test/test_package/child/module1.py"
#     logger.info(f"checking {path}")
#     items = find_pinjected_annotations(str(P_ROOT / "test/test_package/child/module1.py"))
#     assert all(isinstance(item, Annotation) for item in items)
#     logger.info(f"found items:{items}")
#     assert len(items) > 0


def test_test_aggregator():
    agg = PinjectedTestAggregator()
    targets = agg.gather(P_ROOT / "test/test_package")
    logger.info(f"found {len(targets)} target files")
    # logger.info(f"targets: {pformat(targets)}")
    assert len(targets) > 0


@pytest.mark.asyncio
async def test_run_test():
    target = VariableInFile(P_ROOT / "test/test_package/child/module1.py", "test_test_object")
    await d[a_pinjected_run_test(target)]


@pytest.mark.asyncio
async def test_run_test_with_context():
    test_c = VariableInFile(P_ROOT / "test/test_package/child/module1.py", "test_c")
    test_cc = VariableInFile(P_ROOT / "test/test_package/child/module1.py", "test_cc")
    await d[a_pinjected_run_test(test_c)]
    await d[a_pinjected_run_test(test_cc)]


@pytest.mark.asyncio
async def test_run_all_test():
    test_runner = await d[a_pinjected_run_all_test(
            P_ROOT / "test/test_package"
    )]
    async for res in test_runner:
        res:PinjectedTestResult
        if res.failed():
            logger.error(f"{res.target.to_module_var_path().path} -> {res.value}")
        else:
            logger.success(f"{res.target.to_module_var_path().path} -> {res.value}")

@pytest.mark.asyncio
async def test_viz_all_test():
    test_runner = await d[a_pinjected_run_all_test(
            P_ROOT / "test/test_package"
    )]
    visualizer = await d[a_visualize_test_results(test_runner)]
    visualizer


if __name__ == '__main__':
    pass
