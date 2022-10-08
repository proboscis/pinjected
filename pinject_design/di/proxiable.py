from abc import abstractmethod
from dataclasses import dataclass
from typing import Generic, TypeVar, Any

T = TypeVar("T")


class IProxyContext(Generic[T]):

    @abstractmethod
    def getattr(self, tgt: T, name: str):
        pass

    @abstractmethod
    def call(self, tgt: T, *args, **kwargs):
        pass

    @abstractmethod
    def pure(self, tgt: T) -> "DelegatedVar[T]":
        pass

    @abstractmethod
    def getitem(self, tgt: T, key) -> Any:
        pass

    @abstractmethod
    def eval(self, tgt: T):
        pass

    @abstractmethod
    def alias_name(self):
        pass

    @abstractmethod
    def iter(self, tgt: T):
        pass
    @abstractmethod
    def dir(self,tgt):
        pass



@dataclass
class DelegatedVar(Generic[T]):  # Generic Var Type that delegates all implementations to cxt.
    value: T
    cxt: IProxyContext[T]

    def __getattr__(self, item):
        return self.cxt.getattr(self.value, item)

    def __call__(self, *args, **kwargs):
        return self.cxt.call(self.value, *args, **kwargs)

    def __getitem__(self, key):
        return self.cxt.getitem(self.value, key)

    def eval(self):
        """this should return the semantic result of calculation."""
        return self.cxt.eval(self.value)

    def __str__(self):
        return f"{self.cxt.alias_name()}({self.value},{self.cxt})"

    def __iter__(self):
        return self.cxt.iter(self.value)


