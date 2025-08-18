"""Test fixture for nested generic types."""

from pinjected import injected, IProxy
from typing import List, Dict, Optional, Union, Protocol


class User:
    """User model."""

    pass


class Product:
    """Product model."""

    pass


# Test case for Container[T] pattern
user_list_proxy: IProxy[List[User]] = IProxy()
user_dict_proxy: IProxy[Dict[str, User]] = IProxy()
optional_user_proxy: IProxy[Optional[User]] = IProxy()
union_proxy: IProxy[Union[User, Product]] = IProxy()

# Deeply nested
nested_proxy: IProxy[Dict[str, List[Optional[User]]]] = IProxy()


class ProcessUserListProtocol(Protocol):
    def __call__(self) -> int: ...


@injected(protocol=ProcessUserListProtocol)
def process_user_list(users: List[User], max_users: int = 100):
    """Process a list of users."""
    return min(len(users), max_users)


class ProcessUserDictProtocol(Protocol):
    def __call__(self) -> list: ...


@injected(protocol=ProcessUserDictProtocol)
def process_user_dict(users: Dict[str, User], max_keys: int = 100):
    """Process a dictionary of users."""
    keys = list(users.keys())
    return keys[:max_keys]


class ProcessOptionalUserProtocol(Protocol):
    def __call__(self) -> bool: ...


@injected(protocol=ProcessOptionalUserProtocol)
def process_optional_user(user: Optional[User], timeout_ms: int = 1000):
    """Process an optional user."""
    return user is not None


class ProcessDeeplyNestedProtocol(Protocol):
    def __call__(self) -> int: ...


@injected(protocol=ProcessDeeplyNestedProtocol)
def process_deeply_nested(data: Dict[str, List[Optional[User]]], max_count: int = 1000):
    """Process deeply nested generic types."""
    total = sum(len(v) for v in data.values())
    return min(total, max_count)
