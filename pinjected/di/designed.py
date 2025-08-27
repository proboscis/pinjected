from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import Generic, TypeVar, Union, TYPE_CHECKING

from pinjected.di.proxiable import DelegatedVar

if TYPE_CHECKING:
    from typing_extensions import Self
    from pinjected.di.design_interface import Design
    from pinjected.di.injected import Injected

T = TypeVar("T")


class Designed(Generic[T], ABC):
    """
    an abstraction of a value to be created with DI with overriding Design.
    """

    @property
    @abstractmethod
    def design(self) -> "Design":
        pass

    @property
    @abstractmethod
    def internal_injected(self) -> "Injected":
        pass

    @staticmethod
    def from_data(design: "Design", injected: "Injected"):
        return PureDesigned(design, injected)

    @staticmethod
    def bind(target: Union["Injected"]):
        from pinjected import Injected
        from pinjected.di.util import EmptyDesign

        if isinstance(target, DelegatedVar):
            return PureDesigned(EmptyDesign, Injected.ensure_injected(target))
        if isinstance(target, Injected):
            return PureDesigned(EmptyDesign, target)
        if isinstance(target, Callable):
            return Designed.bind(Injected.bind(target))
        raise TypeError("target must be a subclass of Injected")

    def override(self, design: "Design"):
        return PureDesigned(self.design + design, self.internal_injected)

    def map(self, f) -> "Self":
        return Designed.bind(self.internal_injected.map(f)).override(self.design)

    @staticmethod
    def zip(*others: "Self"):
        from pinjected import EmptyDesign, Injected

        d = sum([o.design for o in others], EmptyDesign)
        return Designed.bind(
            Injected.mzip(*[o.internal_injected for o in others])
        ).override(d)

    @property
    def proxy(self):
        from pinjected.di.app_designed import designed_proxy

        return designed_proxy(self)


@dataclass
class PureDesigned(Designed):
    _design: "Design"
    _internal_injected: "Injected"

    @property
    def design(self) -> "Design":
        return self._design

    @property
    def internal_injected(self) -> "Injected":
        return self._internal_injected
