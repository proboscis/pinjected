import abc
from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

from returns.maybe import Maybe, Nothing

from pinjected import Injected
from pinjected.di.metadata.location_data import CodeLocation

T, U = TypeVar("T"), TypeVar("U")


@dataclass
class BindMetadata:
    """
    This is the metadata of a bind.
    """
    code_location: Maybe[CodeLocation] = None
    """
    The location of the binding location, this will be used by the IDE to jump to the binding location.
    """


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

    @property
    def metadata(self) -> Maybe[BindMetadata]:
        return Nothing


@dataclass
class InjectedBind(Bind):
    src: Injected
    metadata: Maybe[BindMetadata] = Nothing

    def to_injected(self) -> Injected:
        return self.src


@dataclass
class MappedBind(Bind[U]):
    src: Bind[T]
    f: Callable[[T], U]

    def to_injected(self) -> Injected:
        return self.src.to_injected().map(self.f)

    @property
    def metadata(self) -> Maybe[BindMetadata]:
        return self.src.metadata
