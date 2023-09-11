from functools import partial
from typing import Callable, Any

from loguru import logger

from pinjected.di.injected import Injected
from pinjected.di.util import instances
from pinjected import Design, injected_function


def _factory(a, b, y=0, x=7):
    assert a == 3
    assert b == 2
    assert x == 5
    return a + b + x


def test_partial():
    d = Design().bind_instance(
        a=1,
        b=2
    ).bind_provider(
        f=Injected.partial(_factory, b=Injected.by_name("b"), x=Injected.pure(5))
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


def test_injected_function_with_defaults():
    @injected_function
    def test_func(x, y, /, a, b, *args, z=7, **mykwargs):
        return x, y, (a, b, *args), mykwargs, z

    @injected_function
    def test_func2(_x,_y, a, b, z=7,s=10):
        return _x, _y, (a, b), z,s


    g = instances(
        x='x',
        y='y',
    ).to_graph()
    expectation = ("x", 'y', (1, 2, 3, 5, 6), {}, 7)
    expectation2 = ("x", 'y', (1, 2, 3, 5, 6), {}, 9)
    expectation3 = ("x", 'y', (1, 2, 3, 5, 6), {'p': 42}, 7)
    expectation4 = ("x", 'y', (1, 2, 3, 5, 6), {'p': 42}, 9)
    expectation5 = ("x", 'y', (1, 2), {}, 7)
    expectation6 = ("x", 'y', (1, 2), 7,10)
    assert g[test_func(1, 2, 3, 5, 6)] == expectation
    assert g[test_func](1, 2, 3, 5, 6) == expectation
    assert g[test_func](1, 2, 3, 5, 6, z=9) == expectation2
    assert g[test_func(1, 2, 3, 5, 6, z=9)] == expectation2
    assert g[test_func(1, 2, 3, 5, 6, p=42)] == expectation3
    assert g[test_func](1, 2, 3, 5, 6, p=42) == expectation3
    assert g[test_func](1, 2, 3, 5, 6, p=42, z=9) == expectation4
    assert g[test_func(1, 2, 3, 5, 6, p=42, z=9)] == expectation4
    assert g[test_func(1, 2)] == expectation5
    assert g[test_func](1, 2) == expectation5
    assert g[test_func2](1, 2) == expectation6
    assert g[test_func2(1, 2)] == expectation6
    assert g[test_func2(1, 2, 7)] == expectation6

