"""Test file for PINJ026 rule: a_ prefixed dependencies should not use Any type."""

from pinjected import injected
from typing import Any, Protocol


# Bad: a_ prefixed dependencies with Any type when protocol is specified
@injected(protocol=ProcessingProtocol)
async def a_process_data(
    a_fetcher: Any,  # PINJ026
    a_processor: Any,  # PINJ026
    logger: Any,  # OK: not a_ prefixed
    /,
    data: str,
) -> str:
    pass


# Good: Proper protocol types for a_ prefixed dependencies
class AFetcherProtocol(Protocol):
    async def fetch(self, data: str) -> dict: ...


class AProcessorProtocol(Protocol):
    async def process(self, data: dict) -> str: ...


@injected(protocol=ProcessingProtocol)
async def a_process_data_good(
    a_fetcher: AFetcherProtocol,  # Good
    a_processor: AProcessorProtocol,  # Good
    logger: Any,  # OK: not a_ prefixed
    /,
    data: str,
) -> str:
    pass


# OK: No protocol parameter, so rule doesn't apply
@injected
async def a_process_without_protocol(
    a_fetcher: Any,  # OK: no protocol parameter
    a_processor: Any,  # OK: no protocol parameter
    /,
    data: str,
) -> str:
    pass


# Bad: Mixed - some a_ deps with Any, some with proper types
@injected(protocol=MixedProtocol)
def mixed_dependencies(
    a_reader: Any,  # PINJ026
    a_writer: AWriterProtocol,  # Good
    non_a_service: Any,  # OK: not a_ prefixed
    /,
    data: str,
) -> str:
    pass


# Bad: Using typing.Any
import typing


@injected(protocol=TypedProtocol)
def typed_any(
    a_service: typing.Any,  # PINJ026
    /,
    data: str,
) -> str:
    pass


# OK: Not @injected
def regular_function(a_param: Any):
    return a_param


# OK: @instance decorator, not @injected
from pinjected import instance


@instance
def a_database(a_config: Any):
    return {"config": a_config}
