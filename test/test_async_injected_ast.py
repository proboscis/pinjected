from sys import stderr, stdout

from pinjected.pinjected_logging import logger

from pinjected import instance, injected, design, Injected


def test_async_ast():
    from pinjected.pinjected_logging import logger
    logger.remove()
    logger.add(stdout, colorize=True)
    @instance
    async def x():
        return 'x'

    @injected
    async def y(x):
        return 'y' + x

    test_design = design()
    logger.info(f"x:{x}")
    logger.info(f"y(x):{y(x)}")
    logger.info(f"y(x) => {y(x).value}")
    logger.info(f"y(injected('x')) => {y(injected('x'))}")
    # why is provided x a coroutine?
    assert test_design.to_graph().provide('x') == 'x'
    assert test_design.to_graph().provide(x) == 'x'

    assert test_design.to_graph().provide(y('x')) == 'yx'
    assert test_design.to_graph().provide(y(x)) == 'yx'

    assert test_design.to_graph().provide(y(injected('x'))) == 'yx'


async def x_provider():
    return 'x'


def test_map():
    x = Injected.pure('x')
    y = x.map(lambda x: f"y{x}")
    d = design(
        x=x,
        y=y
    )
    g = d.to_graph()

    assert g['x'] == 'x'
    assert g['y'] == 'yx'


def test_await_op():
    proxy = Injected.pure(x_provider).proxy().await__()

    d = design(
        x=proxy
    )
    g = d.to_graph()
    logger.info(f"proxy:{proxy}")
    assert g['x'] == 'x'


def test_injected_dict():
    async def y_provider():
        return f"y"

    async def use_x(x):
        return f"used{x}"

    x = Injected.dict(
        x=Injected.pure('x'),
        y=Injected.bind(y_provider),
    )
    d = design(
        x=x,
        use_x=use_x
    )
    g = d.to_graph()
    assert g['x'] == dict(x='x', y='y')


def test_injected_bind():
    async def target(x):
        return x

    bound = Injected.bind(target, x=Injected.pure('z'))
    d = design(
        x=bound
    )
    assert d.provide(bound) == 'z'


def test_async_partial():
    partial = Injected.inject_partially(x_provider)
    d = design(
        x=partial
    )
    g = d.to_graph()
    assert g[partial()] == 'x'


def test_injected():
    from pinjected.pinjected_logging import logger
    logger.remove()
    logger.add(stdout, colorize=True)

    # logger.opt(colors=True,ansi=True)
    async def provide_x():
        logger.info(f"provide_x called.")
        return 'x'

    bound_x = Injected.bind(provide_x)

    @instance
    async def instance_x():
        return 'x'

    partial_x = Injected.inject_partially(provide_x)()
    from pinjected.pinjected_logging import logger
    logger.info(f"partial_x => :{partial_x}")
    logger.info(f"partial x provider:{partial_x.eval().get_provider()}")
    d = design(
        x=Injected.bind(provide_x),
        xx=bound_x,
        partial_x=partial_x,
    )
    g = d.to_graph()
    assert g['x'] == 'x'
    assert g['xx'] == 'x'
    assert g['partial_x'] == 'x'
    assert g['instance_x'] == 'x'


def test_lambda_as_provider():
    provide_x = lambda: 'x'
    provide_y = lambda x: f"y{x}"
    d = design(
        x=Injected.bind(provide_x),
        y=Injected.bind(provide_y)
    )
    g = d.to_graph()
    # assert Injected.bind(provide_y,x=provide_x).dependencies() == set()
    assert g['x'] == 'x'
    assert g['y'] == 'yx'
