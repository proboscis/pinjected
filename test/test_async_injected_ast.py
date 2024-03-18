from pinjected import instance, injected, instances, Injected, providers


def test_async_ast():
    from loguru import logger
    @instance
    async def x():
        return 'x'

    @injected
    async def y(x):
        return 'y' + x

    design = instances()
    logger.info(f"x:{x}")
    logger.info(f"y(x):{y(x)}")
    logger.info(f"y(x) => {y(x).value}")
    # why is provided x a coroutine?
    assert design.to_graph().provide('x') == 'x'
    assert design.to_graph().provide(x) == 'x'

    assert design.to_graph().provide(y('x')) == 'yx'
    assert design.to_graph().provide(y(x)) == 'yx'

def test_await_op():

    async def get_async_func():
        return 'async x'


    d = providers(
        x = Injected.pure(get_async_func).proxy()
    )
    g = d.to_graph()
    assert g['x'] == 'async x'


def test_injected():
    async def provide_x():
        logger.info(f"provide_x called.")
        return 'x'

    bound_x = Injected.bind(provide_x)

    @instance
    async def instance_x():
        return 'x'

    partial_x = Injected.partial(provide_x)()
    from loguru import logger
    logger.info(f"partial_x => :{partial_x}")
    logger.info(f"partial x provider:{partial_x.eval().get_provider()}")
    d = providers(
        x=provide_x,
        xx=bound_x,
        partial_x=partial_x,
    )
    g = d.to_graph()
    assert g['x'] == 'x'
    assert g['xx'] == 'x'
    assert g['partial_x'] == 'x'
    assert g['instance_x'] == 'x'
