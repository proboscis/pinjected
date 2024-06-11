from returns.result import safe, Failure

from pinjected import instances


def test_provide_session():
    d = instances(
        a=0
    )
    g = d.to_graph()
    assert g["__resolver__"] == g.resolver


def test_child_session():
    d = instances(
        a=0
    ).bind_provider(
        x=lambda a: a
    )
    g = d.to_graph()
    child_g = g.child_session(instances(a=1))
    grandchild_g = child_g.child_session(instances(a=2))
    assert g["a"] == 0
    assert child_g['a'] == 1  # ah, this is actually an expected behavior.
    assert grandchild_g['a'] == 2
    assert child_g['a'] == 1  # oh why is this 0??
    assert g["a"] == 0
    assert g["x"] == 0
    assert child_g['x'] == 0  # x is already in parent, and is not overriden explicitly.
    # for this to work we need to track all the dependenciy tree of a binding.
    from loguru import logger
    logger.info(grandchild_g)
    logger.info(grandchild_g.resolver._design_from_ancestors().bindings)
    assert grandchild_g['x'] == 0
    assert child_g['x'] == 0  # oh why is this 0??
    assert g["x"] == 0
    # so in order to make session work,
    # you must specify all the components,
    # implicit components in child session will be forgotten.

