from pinjected import providers, injected, Design
from pinjected.visualize_di import DIGraph


def test_distil_design():
    d = providers(
        x=lambda: 0,
        # y = lambda x: x,
        y=injected("x") + 1,
        z=lambda x, y: x + y,
    )
    vg: DIGraph = DIGraph(d)
    print(vg.distilled('z'))
