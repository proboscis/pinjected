from abc import ABC, abstractmethod
from typing import Generic

from pinjected.di.proxiable import T


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
    def is_instance(self, item) -> bool:
        pass

    def dict(self, **kwargs: T) -> T:
        items = list(kwargs.items())
        keys = [t[0] for t in items]
        values = [t[1] for t in items]
        from loguru import logger
        # logger.info(f"keys:{keys}")
        # logger.info(f"values:{values}")
        def mapper(vs):
            # logger.info(f"mapping:{vs}")
            # here vs are all coroutines.
            return dict(zip(keys, vs))

        return self.zip(*values).map(mapper)

    def _await_(self, tgt: T):
        raise NotImplementedError("await not implemented")
