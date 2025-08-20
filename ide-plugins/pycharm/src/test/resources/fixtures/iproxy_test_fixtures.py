"""Test fixtures for IProxy gutter icon provider tests."""

from pinjected import IProxy, injected, Injected
from typing import List, Dict, Optional, Union, Tuple, Protocol, TypeVar, Generic


# Define test classes
class User:
    """Test User class."""

    pass


class Product:
    """Test Product class."""

    pass


# Test case 1: Simple IProxy variables
user_proxy: IProxy[User] = IProxy()
product_proxy: IProxy[Product] = IProxy()

# Test case 2: Nested generic types
list_proxy: IProxy[List[User]] = IProxy()
dict_proxy: IProxy[Dict[str, User]] = IProxy()
nested_list: IProxy[List[List[Product]]] = IProxy()

# Test case 3: Complex type parameters
optional_proxy: IProxy[Optional[User]] = IProxy()
union_proxy: IProxy[Union[User, Product]] = IProxy()
tuple_proxy: IProxy[Tuple[User, Product, str]] = IProxy()


# Test case 4: IProxy inside class (should be ignored)
class MyClass:
    class_proxy: IProxy[User] = IProxy()

    def __init__(self):
        self.instance_proxy: IProxy[Product] = IProxy()


# Test case 5: IProxy without type parameter (rare)
bare_proxy: IProxy = IProxy()

# Test case 6: Non-IProxy variables (should be ignored)
regular_var: str = "test"
regular_list: List[User] = []
injected_var: Injected[User] = Injected()

# Test case 7: IProxy with custom generic classes
T = TypeVar("T")


class Container(Generic[T]):
    pass


container_proxy: IProxy[Container[User]] = IProxy()

# Test case 8: Multiple IProxy on same line (Python allows this)
proxy1: IProxy[User] = IProxy()
proxy2: IProxy[Product] = IProxy()


# Protocol definitions for @injected functions
class ProcessUserProtocol(Protocol):
    def __call__(self) -> str: ...


class ProcessProductProtocol(Protocol):
    def __call__(self) -> dict: ...


class ProcessListProtocol(Protocol):
    def __call__(self) -> list: ...


# @injected functions that should match IProxy[User]
@injected(protocol=ProcessUserProtocol)
def process_user(user: User) -> str:
    """Process a single user."""
    return f"Processed {user}"


@injected(protocol=ProcessUserProtocol)
def validate_user(user: User) -> str:
    """Validate user data."""
    return "Valid" if user else "Invalid"


# @injected functions that should match IProxy[Product]
@injected(protocol=ProcessProductProtocol)
def analyze_product(product: Product) -> dict:
    """Analyze product metrics."""
    return {"product": product}


# @injected functions that should match IProxy[List[User]]
@injected(protocol=ProcessListProtocol)
def batch_process_users(users: List[User]) -> list:
    """Process multiple users."""
    return [f"Processed {u}" for u in users]


# Functions with multiple parameters (only first non-default param matters)
@injected(protocol=ProcessUserProtocol)
def export_user(user: User, indent_size: int = 2) -> str:
    """Export user with specified indentation."""
    indent = " " * indent_size
    return f"{indent}Exported {user}"


# Invalid @injected functions (multiple non-default params)
class InvalidMultiParamsProtocol(Protocol):
    def __call__(self, user: User, product: Product) -> str: ...


@injected(protocol=InvalidMultiParamsProtocol)
def invalid_multi_params(user: User, product: Product) -> str:
    """This should NOT match - has multiple required params."""
    return f"{user} bought {product}"


# Regular functions without @injected (should NOT appear)
def regular_function(user: User) -> str:
    """Regular function without @injected."""
    return str(user)
