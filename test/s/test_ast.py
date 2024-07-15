from pinjected.di.ast_expr import Expr, Object


def test_expr():
    expr = Object(0)
    print(expr.origin_frame)