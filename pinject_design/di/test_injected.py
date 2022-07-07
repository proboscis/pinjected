from functools import partial
from typing import Callable, Any

from loguru import logger

from pinject_design.di.injected import Injected
from pinject_design.di.util import Design


def _factory(a, b, x):
    return a + b + x


def test_partial():
    d = Design().bind_instance(
        a=1,
        b=2
    ).bind_provider(
        f=Injected.partial(_factory, "a", "b")
    )
    f: Callable[[int], Any] = d.provide("f")
    applied: Callable[[int], Any] = partial(_factory, 0, 0)

    assert partial(_factory, 0, b=0)(x=1) == 1
    fx = f(3)
    logger.info(f)
    assert fx == 6
