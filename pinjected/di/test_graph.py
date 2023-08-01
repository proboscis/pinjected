from returns.result import safe, Failure

from pinjected import Design


def test_provide_session():
    d = Design().bind_instance(
        a=0
    )
    g = d.to_graph()
    assert g["session"] == g


def test_child_session():
    d = Design().bind_instance(
        a=0
    ).bind_provider(
        x=lambda a: a
    )
    g = d.to_graph()
    child_g = g.child_session(Design().bind_instance(a=1))
    grandchild_g = child_g.child_session(Design().bind_instance(a=2))
    assert g["a"] == 0
    assert child_g['a'] == 1  # ah, this is actually an expected behavior.
    assert grandchild_g['a'] == 2
    assert child_g['a'] == 1  # oh why is this 0??
    assert g["a"] == 0
    assert g["x"] == 0
    assert child_g['x'] == 0  # x is already in parent, and is not overriden explicitly.
    # for this to work we need to track all the dependenciy tree of a binding.
    assert grandchild_g['x'] == 0
    assert child_g['x'] == 0  # oh why is this 0??
    assert g["x"] == 0
    # so in order to make session work,
    # you must specify all the components,
    # implicit components in child session will be forgotten.


def test_proxied():
    d= Design().bind_instance(
    ).bind_provider(
        y = lambda x:x+1
    )
    g = d.to_graph()
    evaluated = g.proxied("y").eval()
    print(evaluated)
    assert isinstance(safe(evaluated.run)(),Failure)
    assert evaluated.override(Design().bind_instance(x=1)).run() == 2
    assert evaluated.override(Design().bind_instance(x=2)).run() == 3
