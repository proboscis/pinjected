from functools import partial
from typing import Callable, Any

from loguru import logger

from pinject_design.di.injected import Injected, injected_function, injected_function2
from pinject_design.di.util import Design, instances


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


def test_injected_function():
    @injected_function
    def test_func(_x, _y, /, *args, **mykwargs):
        assert args, "args should be non-empty"
        return _x + _y + str(args)

    g = instances(
        x='x',
        y='y',
    ).to_graph()
    assert g[test_func](1, 2, 3, 5, 6) == 'x' + 'y' + '(1, 2, 3, 5, 6)'


def test_injected_function2():
    @injected_function2
    def test_func(x, y, /, *args, **mykwargs):
        assert args, "args should be non-empty"
        return x + y + str(args)

    g = instances(
        x='x',
        y='y',
    ).to_graph()
    assert g[test_func](1, 2, 3, 5, 6) == 'x' + 'y' + '(1, 2, 3, 5, 6)'
