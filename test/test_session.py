from pinjected import injected, design, instance


def test_access_session():
    @instance
    async def task(__resolver__):
        print(__resolver__)
        pass

    d = design()

    return d.provide(task)
