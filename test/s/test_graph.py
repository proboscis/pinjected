from pprint import pprint

from pinject_design import Design, injected_function, Injected
from pinject_design.di.graph import MyObjectGraph, IObjectGraph
from pinject_design.di.util import instances


async def asynz_zz(x, y, z):
    return x, y, z


design = Design().bind_instance(
    x=0
).bind_provider(
    y=lambda x: x + 1,
    z=lambda y: y + 1,
    zz=asynz_zz
)


@injected_function
def test_factory(x, y, /, a):
    return x, y, a


def test_provide():
    g = MyObjectGraph.root(design)
    g2 = g.child_session(instances(
        y=10
    ))
    assert g["y"] == 1
    assert g["z"] == 2
    assert g["zz"] == (0, 1, 2)
    assert isinstance(g['session'], IObjectGraph)
    assert g2['y'] == 10
    assert g2[test_factory](2) == (0, 10, 2)
    pprint(g2.resolver.dependency_tree('zz'))
    pprint(g2.resolver.dependency_tree(Injected.by_name('zz')))
