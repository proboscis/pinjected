from typing import Protocol
from pinjected import IProxy, injected


class User:
    name: str


def some_func():
    return IProxy()


# Test cases - watch the console output!
test_proxy: IProxy[int] = some_func()
user_proxy: IProxy[User] = IProxy()


class ProcessIntProtocol(Protocol):
    def __call__(self, value: int) -> int: ...


@injected(protocol=ProcessIntProtocol)
def process_int(value: int) -> int:
    return value * 2


class ProcessUserProtocol(Protocol):
    def __call__(self, user: User) -> str: ...


@injected(protocol=ProcessUserProtocol)
def process_user(user: User) -> str:
    return user.name
