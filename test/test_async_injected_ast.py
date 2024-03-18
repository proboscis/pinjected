from pinjected import instance, injected, instances


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
    assert design.to_graph().provide(x) == 'x'
    assert design.to_graph().provide(y('x')) == 'yx'
    assert design.to_graph().provide(y(x)) == 'yx'


