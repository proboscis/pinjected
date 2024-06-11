from pinjected.v2.events import ResolverEvent


class IResolverCallback:
    def __call__(self, event: ResolverEvent):
        pass
