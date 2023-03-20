from functools import partial
from typing import Callable, Any

from loguru import logger

from pinject_design.di.injected import Injected, injected_function
from pinject_design.di.util import Design, instances


def _factory(a, b, x):
    assert a == 3
    assert b == 2
    assert x == 5
    return a + b + x


def test_partial():
    d = Design().bind_instance(
        a=1,
        b=2
    ).bind_provider(
        f=Injected.partial(_factory,b=Injected.by_name("b"),x=Injected.pure(5))
    )
    assert d.provide("f")(3) == 10


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