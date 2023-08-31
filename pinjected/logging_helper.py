from contextlib import contextmanager
from loguru import logger


@contextmanager
def disable_internal_logging():
    # logger.info(f"disabling internal logging")
    names = [
        'pinjected.di.graph',
        'pinjected.helpers',
        'pinjected.module_inspector',
        'pinjected'
    ]
    for n in names:
        logger.disable(n)
    yield
    for n in names:
        logger.enable(n)
    # logger.info(f"enabling internal logging")
