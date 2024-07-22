from returns.result import safe, Failure

from pinjected import instances, Injected
from pinjected.v2.keys import StrBindKey


def test_provide_session():
    d = instances(
        a=0
    )
    g = d.to_graph()
    assert g["__resolver__"] == g.resolver




def test_child_session():
    d = instances(
        #a=0
    ).bind_provider(
        x=lambda a: a
    )
    g = d.to_graph()
    child_g = g.child_session(instances(a=1))
    grandchild_g = child_g.child_session(instances(a=2))
    request_a = Injected.bind(lambda a: a + a).proxy
    a_plus_a = request_a + request_a

    #assert g["a"] == 0
    # when there is no binding in the initial d, you don't get 'a' in the children either
    assert child_g['a'] == 1  # ah, this is actually an expected behavior.
    assert child_g[request_a] == 2
    assert child_g[a_plus_a] == 4
    assert grandchild_g['a'] == 2
    assert child_g['a'] == 1  # oh why is this 0??
    #assert g["a"] == 0
    #assert g["x"] == 0
    assert child_g['x'] == 1  # x is already in parent, and is not overriden explicitly.
    # Ah! so,,, when there is no binding for x in the child, it uses the parent.
    # but parent resolver has no idea about its children. so it can't use its child.
    """
    So my algo is like this
    
    request X:
    X -> child -> parent
                  parent finds Y is missing
                  parent has no Y.
         child <- ask child for Y
         child has Y
         child -> Y
    """


    # for this to work we need to track all the dependenciy tree of a binding.
    from loguru import logger
    logger.info(grandchild_g)
    logger.info(grandchild_g.resolver._design_from_ancestors().bindings)
    objs = grandchild_g.resolver.objects
    objs.pop(StrBindKey('__resolver__'))
    objs.pop(StrBindKey('__design__'))
    assert grandchild_g['a'] == 2
    assert grandchild_g['x'] == 2, f"grandchild.objects:{objs}"
    assert child_g['x'] == 1  # oh why is this 0??
    #assert g["x"] == 0
    # so in order to make session work,
    # you must specify all the components,
    # implicit components in child session will be forgotten.
