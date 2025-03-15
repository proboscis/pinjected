from pinjected import design, injected, Design, Injected
from pinjected.visualize_di import DIGraph


def test_distil_design():
    d = design(
        x=Injected.bind(lambda: 0),
        # y = lambda x: x,
        y=injected("x") + 1,
        z=Injected.bind(lambda x, y: x + y),
    )
    vg: DIGraph = DIGraph(d)
    print(vg.distilled('z'))
