from dataclasses import dataclass
from typing import TypeVar, Any, Callable, Generic, Iterator

from pinject_design.di.proxiable import IProxyContext, DelegatedVar

T = TypeVar("T")
U = TypeVar("U")


@dataclass
class DynamicProxyContextImpl(IProxyContext[T]):
    accessor: Callable[[T], Any]
    pure_impl: Callable[[Any], T]
    _alias_name: str

    def getattr(self, tgt: T, name: str):
        return self.pure(getattr(self.accessor(tgt), name))

    def call(self, tgt: T, *args, **kwargs):
        return self.pure(self.accessor(tgt)(*args, **kwargs))

    def pure(self, tgt: T) -> DelegatedVar[T]:
        return DelegatedVar(self.pure_impl(tgt), self)

    def getitem(self, tgt: T, key) -> Any:
        return self.pure(self.accessor(tgt)[key])

    def eval(self, tgt: T):
        return self.accessor(tgt)

    def alias_name(self):
        return self._alias_name

    def iter(self, tgt: T):
        return DynamicProxyIterator(iter(self.accessor(tgt)), self)

    def dir(self, tgt: T):
        return dir(self.accessor(tgt))


@dataclass
class DynamicProxyIterator(Generic[T]):
    src: Iterator
    cxt: DynamicProxyContextImpl

    def __iter__(self):
        return self

    def __next__(self):
        return self.cxt.pure(next(self.src))
