from dataclasses import dataclass, field
from typing import Optional

from pinjected.v2.keys import IBindKey


@dataclass
class ProvideContext:
    resolver:'AsyncResolver'
    key: Optional[IBindKey]
    parent: Optional['ProvideContext']
    def __post_init__(self):
        if self.key is not None:
            assert isinstance(self.key, IBindKey), f"key must be an instance of IBindKey, not {type(self.key)}"

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





