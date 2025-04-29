from pinjected import design, instance


def test_access_session():
    @instance
    async def task(__resolver__):
        print(__resolver__)

    d = design()

    return d.provide(task)
