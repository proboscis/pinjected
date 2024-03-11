from dataclasses import dataclass
from typing import Optional

from pinjected.v2.keys import IBindKey


@dataclass
class ProvideContext:
    key: Optional[IBindKey]
    parent: Optional['ProvideContext']

    @property
    def trace(self):
        if self.parent is None:
            return [self]
        else:
            return self.parent.trace + [self]

    @property
    def trace_str(self):
        return ' -> '.join([str(x.key.ide_hint_string()) for x in self.trace])

