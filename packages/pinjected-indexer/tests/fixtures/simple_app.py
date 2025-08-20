"""Simple test fixture without positional-only syntax."""

from pinjected import injected, IProxy
from typing import List, Protocol


class User:
    """User model."""

    def __init__(self, name: str, email: str):
        self.name = name
        self.email = email


class Product:
    """Product model."""

    def __init__(self, name: str, price: float):
        self.name = name
        self.price = price


# IProxy variables - these should be detected
user_proxy: IProxy[User] = IProxy()
product_proxy: IProxy[Product] = IProxy()
items_proxy: IProxy[List[Product]] = IProxy()


class VisualizeUserProtocol(Protocol):
    def __call__(self) -> str: ...


@injected(protocol=VisualizeUserProtocol)
def visualize_user(user: User):
    """Create a visualization of the user profile."""
    return f"Visualizing {user.name}"


class ValidateUserDataProtocol(Protocol):
    def __call__(self) -> bool: ...


@injected(protocol=ValidateUserDataProtocol)
def validate_user_data(user: User) -> bool:
    """Validate user data integrity."""
    return bool(user.name and user.email)


class AExportUserJsonProtocol(Protocol):
    async def __call__(self) -> str: ...


@injected(protocol=AExportUserJsonProtocol)
async def a_export_user_json(user: User) -> str:
    """Export user data as JSON."""
    return f'{{"name": "{user.name}", "email": "{user.email}"}}'


class AnalyzeProductProtocol(Protocol):
    def __call__(self) -> dict: ...


@injected(protocol=AnalyzeProductProtocol)
def analyze_product(product: Product) -> dict:
    """Analyze product metrics."""
    return {"name": product.name, "price": product.price, "category": "unknown"}


class ProcessProductListProtocol(Protocol):
    def __call__(self) -> dict: ...


@injected(protocol=ProcessProductListProtocol)
def process_product_list(products: List[Product], currency: str = "USD"):
    """Process a list of products."""
    total = sum(p.price for p in products)
    return {"total": total, "count": len(products), "currency": currency}


# This should NOT be detected (no @injected decorator)
def regular_function(user: User):
    """Regular function without @injected."""
    return user.name
