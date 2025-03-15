from pinjected import Injected, EmptyDesign, design
from pinjected.v2.async_resolver import AsyncResolver


def test_injected_proxy():
    from pinjected.pinjected_logging import logger
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

    d = design(
        x=0,
        x0=0,
        y=Injected.bind(lambda x: x + 1),
        z=Injected.bind(lambda y: y + 1),
        x1=Injected.bind(lambda x0: x0 + 1),
        x2=Injected.bind(lambda x1: x1 + 1),
        x3=Injected.bind(lambda x2: x2 + 1),
        x4=Injected.bind(lambda x3: x3 + 1),
        x5=Injected.bind(lambda x4: x4 + 1),
        x6=Injected.bind(lambda x5: x5 + 1),
        x7=Injected.bind(lambda x6: x6 + 1)
    )
    g = AsyncResolver(d).to_blocking()
    assert g['z'] == 2
    assert g['x7'] == 7

