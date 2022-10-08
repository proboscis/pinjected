from dataclasses import dataclass
from typing import List, Any


@dataclass
class DependencyResolutionFailure:
    key: str
    trace: List[str]
    cause: Any

    def trace_str(self):
        return ' => '.join(self.trace)

    def explanation_str(self):
        return f"failed to find dependency: {self.key} at {self.trace_str()}"

    def __repr__(self):
        return f"DependencyResolutionFailure(key:{self.key}\t,trace:{self.trace_str()},cause: ({self.cause})"


class _MissingDepsError(RuntimeError):
    def __init__(self, msg: str, name: str, trace: List[str]):
        super().__init__(msg)
        self.name = name
        self.trace = trace.copy()

    def __getstate__(self):
        return self.msg, self.name, self.trace

    def __setstate__(self, data):
        self.msg, self.name, self.trace = data