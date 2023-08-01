import abc
from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

from pinjected import Injected

T, U = TypeVar("T"), TypeVar("U")


class Bind(Generic[T], metaclass=abc.ABCMeta):

    def map(self, f: Callable[[T], U]) -> "Bind[U]":
        return MappedBind(self, f)

    @staticmethod
    def provider(provider):
        return InjectedBind(Injected.bind(provider))

    @staticmethod
    def injected(injected: Injected) -> "Bind":
        return InjectedBind(injected)

    @staticmethod
    def instance(instance: object):
        return InjectedBind(Injected.pure(instance))

    @staticmethod
    def clazz(cls: type):
        return InjectedBind(Injected.bind(cls))

    @abc.abstractmethod
    def to_injected(self) -> Injected:
        raise NotImplementedError("to_injected must be implemented")

    def __call__(self, *args, **kwargs):
        return self.to_injected().get_provider()(*args, **kwargs)


@dataclass
class InjectedBind(Bind):
    src: Injected

    def to_injected(self) -> Injected:
        return self.src


@dataclass
class MappedBind(Bind[U]):
    src: Bind[T]
    f: Callable[[T], U]
