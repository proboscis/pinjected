"""
Example Python file to demonstrate dependency injection patterns.
"""
from typing import Any


class Database:
    """Simple database class."""
    
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        
    def query(self, sql: str) -> list[dict[str, Any]]:
        """Execute a query."""
        print(f"Querying with {sql} on {self.connection_string}")
        return [{"result": "example"}]


class Logger:
    """Simple logger class."""
    
    def __init__(self, log_level: str = "INFO"):
        self.log_level = log_level
        
    def log(self, message: str) -> None:
        """Log a message."""
        print(f"[{self.log_level}] {message}")


class UserRepository:
    """Repository with dependencies injected through the constructor."""
    
    def __init__(self, database: Database, logger: Logger):
        self.database = database
        self.logger = logger
        
    def get_users(self) -> list[dict[str, Any]]:
        """Get all users."""
        self.logger.log("Fetching users")
        return self.database.query("SELECT * FROM users")


class UserService:
    """Service that uses the repository."""
    
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository
        
    def get_active_users(self) -> list[dict[str, Any]]:
        """Get active users."""
        return self.user_repository.get_users()


# Example usage of these classes
if __name__ == "__main__":
    # Manual dependency injection
    db = Database("sqlite:///users.db")
    logger = Logger("DEBUG")
    repo = UserRepository(db, logger)
    service = UserService(repo)
    
    # Using the service
    users = service.get_active_users()
    print(users)
