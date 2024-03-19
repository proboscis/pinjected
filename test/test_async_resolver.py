from pinjected import instances, providers, injected, instance

d = instances(
    x=0
) + providers(

)



def test_async_resolver():
    @instance
    async def y(x, /):
        from loguru import logger
        logger.info(f"running y")
        return x + 1


    @instance
    def z(x, /):
        return x + 1


    @injected
    def alpha(y, z, /):
        return y + z


    g = d.to_graph()
    assert g['y'] == 1
    assert g['z'] == 1
    assert g[alpha()] == 2
