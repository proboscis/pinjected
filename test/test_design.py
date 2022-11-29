from pinject_design import Design, Injected, EmptyDesign
from pinject_design.di.designed import Designed


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

