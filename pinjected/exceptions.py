from dataclasses import dataclass
from typing import List, Any

from pinjected.di.validation import ValFailure


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
        return f"DependencyResolutionFailure(key:{self.key},trace:{self.trace_str()},cause: ({self.cause})"


class DependencyResolutionError(RuntimeError):
    def __init__(self, msg: str, causes: List[DependencyResolutionFailure] = None):
        super().__init__(msg)
        if causes is None:
            causes = []
        self.causes = causes.copy()

class DependencyValidationError(RuntimeError):
    def __init__(self, msg: str, cause:ValFailure):
        super().__init__(msg)
        self.cause=cause

@dataclass
class CyclicDependency:
    key:str
    trace:List[str]
    def __repr__(self):
        trace = self.trace + [self.key]
        trace_str = " -> ".join(trace)
        return f"Cyclic Dependency: {trace_str}"



class _MissingDepsError(RuntimeError):
    def __init__(self, msg: str, name: str, trace: List[str]):
        super().__init__(msg)
        self.name = name
        self.trace = trace.copy()

    def __getstate__(self):
        return self.msg, self.name, self.trace

    def __setstate__(self, data):
        self.msg, self.name, self.trace = data
