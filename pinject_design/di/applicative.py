from abc import ABC, abstractmethod
from typing import Generic

from pinject_design.di.proxiable import T


class Applicative(Generic[T], ABC):
    @abstractmethod
    def map(self, target: T, f) -> T:
        pass

    @abstractmethod
    def zip(self, *targets: T):
        pass

    @abstractmethod
    def pure(self, item) -> T:
        pass

    @abstractmethod
    def is_instance(self, item)->bool:
        pass

    def dict(self, **kwargs: T) -> T:
        items = list(kwargs.items())
        keys = [t[0] for t in items]
        values = [t[1] for t in items]
        return self.zip(*values).map(lambda vs: dict(zip(keys, vs)))
