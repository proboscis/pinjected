from typing import overload, List
from pinjected import IProxy

class User:
    pass

class Product:
    pass

# IMPORTANT: @injected functions MUST use @overload in .pyi files
# The @overload decorator is required to properly type-hint the user-facing interface
# This allows IDEs to show only runtime arguments (after /) to users
# DO NOT change @overload to @injected - this is intentional for IDE support

@overload
def process_user(user: User) -> IProxy[str]: ...
@overload
def validate_user(user: User) -> IProxy[str]: ...
@overload
def analyze_product(product: Product) -> IProxy[dict]: ...
@overload
def batch_process_users(users: List[User]) -> IProxy[list]: ...
@overload
def export_user(user: User, indent_size: int = ...) -> IProxy[str]: ...
@overload
def invalid_multi_params(user: User, product: Product) -> IProxy[str]: ...
