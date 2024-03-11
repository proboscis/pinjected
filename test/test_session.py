from pinjected import injected, instances, instance


def test_access_session():
    @instance
    async def task(__resolver__):
        print(__resolver__)
        pass

    d = instances()

    return d.provide(task)
