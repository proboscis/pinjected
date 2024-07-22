from pinjected import Injected, Designed
from pinjected.di.static_proxy import ast_proxy
from pinjected.di.expr_util import Object


def test_expr():
    print(Object("x").test.x.y[0])


# def test_ast_proxy():
#     print(ast_proxy("hello").test.x.y.z[0].eval())


def test_eval_injected():
    tgt = Injected.pure("hello").proxy.x.y.z
    a = Injected.pure("a").proxy
    b = Injected.pure("b").proxy
    ast = tgt(a, b=b)
    print(ast)
    print(ast.eval())
