"""Test file for verifying indexer module paths"""

from pinjected import injected, IProxy
from typing import List, Protocol, Any
from loguru import logger as Logger


# Dummy classes and protocols for testing
class User:
    pass


class Product:
    pass


class Database:
    pass


class Dep1Protocol(Protocol):
    """Protocol for dep1 dependency"""

    pass


class Dep2Protocol(Protocol):
    """Protocol for dep2 dependency"""

    pass


# IProxy variable
user_proxy: IProxy[User] = None


# Protocols for @injected functions
class AFeatureProtocol(Protocol):
    def __call__(self, user: User, opt_param: Any = None) -> str: ...


class AExportUserJsonProtocol(Protocol):
    async def __call__(self, user: User) -> dict: ...


class ProcessItemsProtocol(Protocol):
    def __call__(self, items: List[Product]) -> List[Product]: ...


@injected(protocol=AFeatureProtocol)
def a_feature(dep1: Dep1Protocol, dep2: Dep2Protocol, /, user: User, opt_param=None):
    """Feature that processes a user"""
    return f"Processing user: {user}"


@injected(protocol=AExportUserJsonProtocol)
async def a_export_user_json(logger: Logger, /, user: User):
    """Async function to export user as JSON"""
    return {"user": user}


@injected(protocol=ProcessItemsProtocol)
def process_items(db: Database, /, items: List[Product]):
    """Process a list of products"""
    return items
