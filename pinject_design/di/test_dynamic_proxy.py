from dataclasses import dataclass

from pinject_design import Design, Designed, Injected, EmptyDesign
from pinject_design.di.dynamic_proxy import DynamicProxyContextImpl
from pinject_design.di.graph import SessionValue


@dataclass
class A:
    item: str


def test_dynamic_proxy_iterator():
    ctx = DynamicProxyContextImpl(
        lambda a: a.item,
        A,
        "A_Proxy"
    )
    x = ctx.pure("hello world")
    print(x)
    print(x.split())
    print([i for i in x.split()])


def test_session_value_iterator():
    d = Design().bind_instance(x=0)
    g = d.to_graph()
    session = g.child_session(EmptyDesign)
    ctx = DynamicProxyContextImpl(
        lambda a: a.value,
        lambda x: SessionValue(
            g,
            Designed.bind(Injected.pure(x)),
            session,
        ),
        "SessionValueProxy"
    )
    x = ctx.pure("hello world")
    print(x)
    print(x.split())
    for item in x.split():
        print(item.eval())

    print(g.sessioned("x"))

