from pinjected import injected, IProxy


# Mock class for test
class ServiceImpl:
    pass


@injected
def get_service() -> IProxy:
    return ServiceImpl()
