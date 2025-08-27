"""Simple test for pinjected call CLI command"""

from pinjected import injected, IProxy, design
from typing import Protocol
from loguru import logger
from loguru._logger import Logger


class User:
    def __init__(self, name: str = "Test User"):
        self.name = name


class SimpleProtocol(Protocol):
    def __call__(self, user: User) -> str: ...


@injected(protocol=SimpleProtocol)
def greet_user(logger: Logger, /, user: User) -> str:
    """Simple function that greets a user"""
    result = f"Hello, {user.name}!"
    logger.info(f"Greeting: {result}")
    return result


# Create a design with bindings
__design__ = design(user=User("Alice"), logger=logger)

# Create IProxy with a User instance
user_proxy: IProxy[User] = IProxy(User("Bob"))
