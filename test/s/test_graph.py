from pprint import pprint

from pinjected import Design, injected_function, Injected, design
from pinjected.di.graph import MyObjectGraph, IObjectGraph
from pinjected.v2.async_resolver import AsyncResolver

test_design = design(
    x=0,
    y=Injected.bind(lambda x: x + 1),
    z=Injected.bind(lambda y: y + 1),
    zz=Injected.bind(lambda x, y, z: (x, y, z)),
    alpha=Injected.bind(lambda x, zz: x + zz)
)
g = test_design.to_graph()
g2 = g.child_session(design(
    y=10
))


@injected_function
def test_factory(x, y, /, a):
    return x, y, a


def test_provide():
    assert g['x'] == 0
    assert g['x'] == 0
    assert g["y"] == 1
    assert g["z"] == 2
    assert isinstance(g['__resolver__'], AsyncResolver)
    assert g2['y'] == 10
    assert g2[test_factory](2) == (0, 10, 2)
    assert g2[lambda x,y: x+y] == 10
