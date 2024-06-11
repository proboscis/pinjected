from dataclasses import dataclass, field
from typing import Optional

from pinjected.v2.keys import IBindKey


@dataclass
class ProvideContext:
    resolver:'AsyncResolver'
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
        def key_str(x):
            if x.key is None:
                return 'None'
            return x.key.ide_hint_string()
        return ' -> '.join([key_str(x) for x in self.trace])





