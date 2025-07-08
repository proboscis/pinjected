from pinjected import injected, instance

# This file should have a stub because it has @injected functions


@injected
def fetch_user(db, /, user_id: str):
    """Fetch user from database."""
    return db.get_user(user_id)


@injected
def update_user(db, /, user_id: str, data: dict):
    """Update user in database."""
    return db.update_user(user_id, data)


@injected
def delete_user(db, /, user_id: str):
    """Delete user from database."""
    return db.delete_user(user_id)


@injected
def list_users(db, /, filter: dict | None = None):
    """List users with optional filter."""
    return db.list_users(filter)


@injected
async def a_get_user_stats(stats_api, /, user_id: str):
    """Get user statistics asynchronously."""
    return await stats_api.get_stats(user_id)


# Not @injected - doesn't count
@instance
def database():
    return Database()


def regular_function():
    """Regular function without decorators."""
    return "not injected"


class UserService:
    """Class with methods."""

    @injected
    def get_user_profile(self, user_repo, /, user_id: str):
        """Get full user profile."""
        return user_repo.get_profile(user_id)


# Mock class for example
class Database:
    pass
