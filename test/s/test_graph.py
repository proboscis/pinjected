from pprint import pprint

from pinjected import Design, injected_function, Injected
from pinjected.di.graph import MyObjectGraph, IObjectGraph
from pinjected.di.util import instances



design = Design().bind_instance(
    x=0
).bind_provider(
    y=lambda x: x + 1,
    z=lambda y: y + 1,
    zz=lambda x,y,z: (x,y,z),
    alpha=lambda x,zz: x + zz
)
g = MyObjectGraph.root(design)
g2 = g.child_session(instances(
    y=10
))

@injected_function
def test_factory(x, y, /, a):
    return x, y, a


def test_provide():

    assert g["y"] == 1
    assert g["z"] == 2
    assert isinstance(g['session'], IObjectGraph)
    assert g2['y'] == 10
    assert g2[test_factory](2) == (0, 10, 2)


def test_dependency_tree():
    print(g.resolver.sorted_dependencies('alpha'))
