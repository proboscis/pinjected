from pinjected import Design, Injected, EmptyDesign, instances, providers
from pinjected.di.designed import Designed
from pinjected.di.graph import MyObjectGraph


def test_designed():
    d = Design().bind_instance(
        a=0,
        b=1,
        c=2
    )
    g = d.to_graph()

    def provide_d(c):
        return c + 1

    designed_d = Designed.bind(provide_d)
    designed_d2 = designed_d.override(EmptyDesign.bind_instance(c=1))
    assert g[designed_d] == 3
    assert g[designed_d2] == 2


def test_injected_proxy():
    hello = Injected.pure("hello").proxy
    func_proxy = Injected.pure(lambda x:x+1).proxy
    design = Design().bind_provider(
        x=lambda: 0,
        y=hello,
        z = func_proxy(Injected.pure(1))
    )
    assert design.provide("y") == "hello"
    assert design.provide("z") == 2

def test_design():
    from loguru import logger
    def raise_error():
        raise RuntimeError("dummy error")
    d = instances(
        x = 0,
    ) + providers(
        x0 = raise_error,
        y = lambda x: x + 1,
        z = lambda y: y + 1,
        x1 = lambda x0: x0 + 1,
        x2 = lambda x1: x1 + 1,
        x3 = lambda x2: x2 + 1,
        x4 = lambda x3: x3 + 1,
        x5 = lambda x4: x4 + 1,
        x6 = lambda x5: x5 + 1,
        x7 = lambda x6: x6 + 1,
    )
    g:MyObjectGraph = d.to_graph()
    logger.info(g.scope)
    assert g['z'] == 2
    logger.info(g.scope)
    assert g['x7'] == 7
    logger.info(g.scope)



if __name__ == '__main__':
    test_design()