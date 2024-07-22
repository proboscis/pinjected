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

    def __post_init__(self):
        assert isinstance(self.name, str)

    def ide_hint_string(self):
        if len(self.name) >= 20:
            return f"{self.name[:10]}...{self.name[-10:]}"
        return self.name


@dataclass(frozen=True)
class DestructorKey(IBindKey):
    tgt: IBindKey

    def ide_hint_string(self):
        return f"destructor({self.tgt.ide_hint_string()})"
