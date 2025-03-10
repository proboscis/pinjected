import pytest
from pinjected import Injected,design
from loguru import logger


@pytest.mark.skip(reason="String concatenation with DelegatedVar not supported yet")
def test_f_string():
    d = design()
    a = Injected.pure('a').proxy
    r_add = "right_add" + a
    logger.info(f"r_add:{r_add}")
    logger.info(d.provide(r_add))

