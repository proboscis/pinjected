from typing import overload
from pinjected import IProxy

# IMPORTANT: @injected functions MUST use @overload in .pyi files
# The @overload decorator is required to properly type-hint the user-facing interface
# This allows IDEs to show only runtime arguments (after /) to users
# DO NOT change @overload to @injected - this is intentional for IDE support

@overload
def my_function(arg1: str) -> IProxy[str]: ...
@overload
def another_function(arg2: int) -> IProxy[int]: ...
