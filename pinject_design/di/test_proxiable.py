from pinject_design import Injected, Designed
from pinject_design.di.static_proxy import Object, ast_proxy


def test_expr():
    print(Object("x").test.x.y[0])


def test_ast_proxy():
    print(ast_proxy("hello").test.x.y.z[0].eval())


def test_eval_injected():
    tgt = Injected.pure("hello").proxy.x.y.z
    a = Injected.pure("a").proxy
    b = Injected.pure("b").proxy
    ast = tgt(a, b=b)
    print(ast)
    print(ast.eval())

def test_designed():

    tgt = Designed.bind(Injected.pure("hello")).proxy.x.y.z
    a = Designed.bind(Injected.pure("a")).proxy
    b = Designed.bind(Injected.pure("b")).proxy
    ast = tgt(a, b=b)
    print(ast)
    print(ast.eval())
