from pinjected import design, injected, instance

d = design(
    x=0
)



def test_async_resolver():
    @instance
    async def y(x, /):
        from pinjected.pinjected_logging import logger
        logger.info(f"running y")
        return x + 1


    @instance
    def z(x, /):
        return x + 1


    @injected
    async def alpha(y, z, /):
        return y + z


    g = d.to_graph()
    assert g['y'] == 1
    assert g['z'] == 1
    assert g[alpha()] == 2
