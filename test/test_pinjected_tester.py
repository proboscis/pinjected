
"""
Here i test the functionality of testing module in pinjected.
1.
"""
from pathlib import Path
from pprint import pformat

from pinjected.runnables import get_runnables
from tqdm import tqdm
from loguru import logger

from pinjected.test_helper.test_aggregator import TimeCachedFileAggregator, meta_design_acceptor, \
    Annotation, PinjectedTestAggregator, find_annotations

P_ROOT = Path(__file__).parent.parent

def test_get_runnables():
    # okey so somehow, we need to check if the file is a test target or not.
    """
    1. check file mod time and cache it
    2. see if __meta_design__ is in the file

    or, see the filename and see if it is a test file.

    However, I want to have the test functions along with the implementations.

    """
    agg = TimeCachedFileAggregator(
        cache_path=Path("~/.cache/pinjected_test_cache.shelve").expanduser(),
        accept_file=meta_design_acceptor
    )
    #targets = agg.gather_target_files(P_ROOT / "pinjected")
    targets = agg.gather_target_files(Path("~/repos/proboscis-env-manager").expanduser())
    logger.info(f"found {len(targets)} target files")
    logger.info(f"targets: {pformat(targets)}")

    #runnables = get_runnables(P_ROOT / "pinjected/test_package/child/module1.py")

def test_find_target_variables():
    items = find_annotations(P_ROOT / "pinjected/test_package/child/module1.py")
    assert all(isinstance(item,Annotation) for item in items)
    logger.info(f"found items:{items}")

def test_test_aggregator():
    agg = PinjectedTestAggregator()
    #targets = agg.gather(P_ROOT / "pinjected")
    targets = agg.gather(Path("~/repos/proboscis-env-manager/src").expanduser())
    logger.info(f"found {len(targets)} target files")
    logger.info(f"targets: {pformat(targets)}")

if __name__ == '__main__':
    pass