from typing import overload
from pinjected import IProxy

class User:
    pass

# IMPORTANT: @injected functions MUST use @overload in .pyi files
# The @overload decorator is required to properly type-hint the user-facing interface
# This allows IDEs to show only runtime arguments (after /) to users
# DO NOT change @overload to @injected - this is intentional for IDE support

@overload
def process_int(value: int) -> IProxy[int]: ...
@overload
def process_user(user: User) -> IProxy[str]: ...
