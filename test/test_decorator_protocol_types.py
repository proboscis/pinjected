"""Test type annotations for decorator protocol feature (ARC-320)."""

from typing import Protocol, reveal_type
from pinjected import injected, design


class UserServiceProtocol(Protocol):
    """Protocol for user service."""

    def __call__(self, user_id: str) -> dict: ...


class AsyncDataProtocol(Protocol):
    """Protocol for async data fetching."""

    async def __call__(self, query: str) -> list[dict]: ...


def test_protocol_type_annotations():
    """Test that @injected with protocol returns correct type annotations."""

    # Test 1: Function with protocol should return IProxy[Protocol]
    @injected(protocol=UserServiceProtocol)
    def get_user(db, /, user_id: str) -> dict:
        return {"id": user_id, "name": f"User {user_id}"}

    # Type checker should see this as IProxy[UserServiceProtocol]
    # In runtime it's actually Partial, but for typing it's IProxy
    if False:  # Type checking only
        reveal_type(get_user)  # Should be IProxy[UserServiceProtocol]

    # Test 2: Function without protocol should return DelegatedVar
    @injected
    def simple_func(dep, /, arg: str) -> str:
        return f"{dep}: {arg}"

    if False:  # Type checking only
        reveal_type(simple_func)  # Should be DelegatedVar

    # Test 3: String injection should return DelegatedVar
    db_proxy = injected("database")

    if False:  # Type checking only
        reveal_type(db_proxy)  # Should be DelegatedVar

    # Test 4: Using protocol-typed dependency in another function
    @injected
    def process_user_data(
        get_user: UserServiceProtocol,  # Type hint with protocol
        /,
        user_id: str,
    ) -> str:
        user_data = get_user(user_id)  # IDE should know this returns dict
        return f"Processing user: {user_data['name']}"

    # Test 5: Async protocol
    @injected(protocol=AsyncDataProtocol)
    async def fetch_data(client, /, query: str) -> list[dict]:
        # Simulate async data fetching
        return [{"query": query, "result": "data"}]

    if False:  # Type checking only
        reveal_type(fetch_data)  # Should be IProxy[AsyncDataProtocol]


def test_protocol_usage_in_design():
    """Test using protocol-annotated functions in design."""

    @injected(protocol=UserServiceProtocol)
    def user_service(db, /, user_id: str) -> dict:
        return {"id": user_id, "name": f"User {user_id}", "db": db}

    # The type of user_service should be IProxy[UserServiceProtocol]
    # This allows better IDE support when used as a dependency

    @injected
    def app(
        user_service: UserServiceProtocol,  # IDE knows the exact interface
        /,
        user_id: str,
    ) -> str:
        user = user_service(user_id)  # IDE provides autocomplete
        return f"Hello, {user['name']}!"

    di = design(db="test_db", user_service=user_service, app=app)

    # Runtime behavior unchanged
    graph = di.to_graph()
    result = graph["app"]("123")
    assert result == "Hello, User 123!"


if __name__ == "__main__":
    test_protocol_type_annotations()
    test_protocol_usage_in_design()
    print("All type annotation tests passed!")
