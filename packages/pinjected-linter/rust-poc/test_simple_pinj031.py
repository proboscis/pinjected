from pinjected import instance, injected


# Mock classes for test
class SomeDependency:
    pass


class ServiceImpl:
    def __init__(self, dep):
        self.dep = dep


@instance
def my_service():
    # This should trigger PINJ031
    dep = injected(SomeDependency)
    return ServiceImpl(dep)
