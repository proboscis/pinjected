"""Test file for PINJ016 rule: Missing or invalid protocol parameter."""

from pinjected import injected, instance
from typing import Protocol


# Add mock imports for test examples
class Logger:
    pass


class ExistingProtocol(Protocol):
    pass


# Bad: No protocol parameter
class ProcessDataProtocol(Protocol):
    def __call__(
        self,
    ) -> str: ...


@injected(protocol=ProcessDataProtocol)
def process_data(logger, /, data: str) -> str:
    return data.upper()


# Bad: String literal as protocol
@injected(protocol="ProcessDataProtocol")  # PINJ016: String literal
def process_with_string_protocol(logger, /, data: str) -> str:
    return data.upper()


# Bad: String literal in async function
@injected(protocol="ABatchAdd1Protocol")  # PINJ016: String literal
async def a_batch_add_1(items: list[dict]) -> list[dict]:
    return [dict(x=item["x"] + 1) for item in items]


# Good: Proper protocol class
class ProcessDataProtocol(Protocol):
    def __call__(self, data: str) -> str: ...


@injected(protocol=ProcessDataProtocol)
def process_with_proper_protocol(logger, /, data: str) -> str:
    return data.upper()


# Good: Protocol from import (mock)


@injected(protocol=ExistingProtocol)
async def async_with_imported_protocol(service, /, data: str) -> str:
    return await service.process(data)


# OK: @instance doesn't need protocol
@instance
def logger():
    return Logger()


# OK: Regular function
def regular_function(data: str) -> str:
    return data.upper()
