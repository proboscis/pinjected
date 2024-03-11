import abc
from abc import ABC
from dataclasses import dataclass


class IBindKey(ABC):
    """
    hold a providing key and metadata
    """
    pass

    @abc.abstractmethod
    def ide_hint_string(self):
        return repr(self)


@dataclass(frozen=True)
class StrBindKey(IBindKey):
    name: str

    def ide_hint_string(self):
        return self.name
