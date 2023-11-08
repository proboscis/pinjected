from pinjected import Design, Injected, EmptyDesign, instances, providers
from pinjected.di.designed import Designed


def test_designed():
    d = Design().bind_instance(
        a=0,
        b=1,
        c=2
    )
    g = d.to_graph()

    def provide_d(c):
        return c + 1

    def check_events(__pinjected_events__):
        __pinjected_events__.register(print)


    g = d.to_graph()
    g[check_events]
    g[provide_d]
