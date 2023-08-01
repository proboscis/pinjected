from pinjected.di.ast import Expr, Object


def test_expr():
    expr = Object(0)
    print(expr.origin_frame)