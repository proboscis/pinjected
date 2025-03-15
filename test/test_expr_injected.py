from pinjected import injected, instance, Injected, design
from pinjected.pinjected_logging import logger
from pinjected.di.app_injected import await_awaitables


@injected
async def test_x():
    # this, calls x three times. how can I avoid that?

    logger.info(f'calling x')
    return "x"


@injected
def test_y(a, b, c):
    return a, b, c


alpha: Injected = test_x()
beta: Injected = test_y(alpha, alpha, alpha)


def test_compilation():
    from pinjected.di.app_injected import await_awaitables
    logger.info(f"AST:\n{beta}")
    await_awaitables(beta.value)


def test_eval_beta():
    g = design().to_graph()
    result = g.provide(beta)
    # 'Call' gets replaced
    print(f'alpha id:{id(alpha.eval().ast), id(alpha.eval().ast)}')
    # as a result of eval() we get different ast instances.
    print(f'result:{result}')


def test_expr_in_design():
    g = design(
        gamma=beta + beta
    ).to_graph()
    result = g.provide('gamma')
    print(result)
