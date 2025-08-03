from typing import overload
from typing import Any, Protocol
from pinjected import IProxy

class MyClaudeCommandProtocol(Protocol):
    def __call__(self) -> str: ...

async def example_usage() -> Any: ...

async def example_with_custom_path() -> Any: ...

async def run_all_examples() -> Any: ...

class CityInfo:
    name: str
    country: str
    population: int
    is_capital: bool

@overload
def my_claude_command() -> IProxy[str]: ...
