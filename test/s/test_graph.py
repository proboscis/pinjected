from pprint import pprint

from pinjected import Design, injected_function, Injected
from pinjected.di.graph import MyObjectGraph, IObjectGraph
from pinjected.di.util import instances
from pinjected.v2.async_resolver import AsyncResolver

design = instances(
    x=0
).bind_provider(
    y=lambda x: x + 1,
    z=lambda y: y + 1,
    zz=lambda x, y, z: (x, y, z),
    alpha=lambda x, zz: x + zz
)
g = design.to_graph()
g2 = g.child_session(instances(
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
