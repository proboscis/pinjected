from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING

from pinjected.v2.keys import IBindKey

if TYPE_CHECKING:
    from pinjected.v2.async_resolver import AsyncResolver


@dataclass
class ProvideContext:
    resolver: "AsyncResolver"
    key: IBindKey | None
    parent: Optional["ProvideContext"]

    def __post_init__(self):
        if self.key is not None:
            assert isinstance(self.key, IBindKey), (
                f"key must be an instance of IBindKey, not {type(self.key)}"
            )

    @property
    def trace(self):
        if self.parent is None:
            return [self]
        return self.parent.trace + [self]

    @property
    def trace_str(self):
        def key_str(x):
            if x.key is None:
                return "None"
            return x.key.ide_hint_string()

        return " -> ".join([key_str(x) for x in self.trace])
