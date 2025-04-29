from dataclasses import dataclass
from typing import Any

from returns.io import IOResultE


@dataclass
class DependencyResolutionFailure:
    key: str
    trace: list[str]
    cause: Any

    def trace_str(self):
        return " => ".join(self.trace)

    def explanation_str(self):
        """
        Generate a detailed explanation of the dependency resolution failure.

        Returns:
            str: A formatted string explaining the dependency resolution failure
                 with trace information.
        """
        return f"Failed to find dependency: {self.key}\nDependency chain: {self.trace_str()}\nCause: {self.cause}"

    def __repr__(self):
        return f"DependencyResolutionFailure(key:{self.key},trace:{self.trace_str()},cause: ({self.cause})"


class DependencyResolutionError(RuntimeError):
    def __init__(self, msg: str, causes: list[DependencyResolutionFailure] = None):
        super().__init__(msg)
        if causes is None:
            causes = []
        self.msg = msg
        self.causes = causes.copy()


class DependencyValidationError(RuntimeError):
    def __init__(self, msg: str, cause: IOResultE):
        super().__init__(msg)
        self.cause = cause


@dataclass
class CyclicDependency:
    key: str
    trace: list[str]

    def __repr__(self):
        trace = self.trace + [self.key]
        trace_str = " -> ".join(trace)
        return f"Cyclic Dependency: {trace_str}"


class _MissingDepsError(RuntimeError):
    def __init__(self, msg: str, name: str, trace: list[str]):
        super().__init__(msg)
        self.name = name
        self.trace = trace.copy()

    def __getstate__(self):
        return self.msg, self.name, self.trace

    def __setstate__(self, data):
        self.msg, self.name, self.trace = data
