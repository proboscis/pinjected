from pinjected import Injected, EmptyDesign, instances, providers
from pinjected.v2.resolver import AsyncResolver
from logugu import logger

def test_injected_proxy():
    hello = Injected.pure("hello").proxy
    func_proxy = Injected.pure(lambda x: x + 1).proxy
    # hmm,
    design = EmptyDesign.bind_provider(
        x=lambda: 0,
        y=hello,
        z=func_proxy(Injected.pure(1))
    )
    logger.info(design.bindings)
    assert design.provide("y") == "hello"
    assert design.provide("z") == 2


def test_design():

    d = instances(
        x=0,
        x0 =0
    ) + providers(
        y=lambda x: x + 1,
        z=lambda y: y + 1,
        x1=lambda x0: x0 + 1,
        x2=lambda x1: x1 + 1,
        x3=lambda x2: x2 + 1,
        x4=lambda x3: x3 + 1,
        x5=lambda x4: x4 + 1,
        x6=lambda x5: x5 + 1,
        x7=lambda x6: x6 + 1,
    )
    g = AsyncResolver(d).to_blocking()
    assert g['z'] == 2
    assert g['x7'] == 7

