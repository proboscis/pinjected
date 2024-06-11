from dataclasses import dataclass


class ValResult:
    pass


@dataclass
class ValSuccess(ValResult):
    pass


@dataclass
class ValFailure(ValResult):
    exc: Exception
