from typing import overload
from pinjected import IProxy

@overload
def process_data(data: str) -> IProxy[str]: ...
@overload
def validate_input(input_data: dict) -> IProxy[bool]: ...
