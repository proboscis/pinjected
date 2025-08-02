"""
Example demonstrating the PyCharm plugin navigation feature.

Click on parameter names in @injected/@instance functions to navigate
to their corresponding function definitions.
"""

from pinjected import injected, instance


# Example 1: Simple @instance function
@instance
def database_connection(host, port):
    """Provides a database connection."""
    return f"DB connection to {host}:{port}"


# Example 2: @instance function with dependencies
@instance
def user_repository(database_connection, logger):
    """Repository that depends on database_connection and logger."""
    return f"UserRepo with {database_connection}"


# Example 3: @injected function with dependencies
@injected
def fetch_users(user_repository, logger, /, user_id=None):
    """
    Click on 'user_repository' or 'logger' parameters to navigate
    to their definitions.
    """
    logger.info(f"Fetching users with id: {user_id}")
    return user_repository.get_users(user_id)


# Example 4: Multiple functions with same name
@instance
def logger():
    """Basic logger instance."""
    return "BasicLogger"


@injected
def logger(log_level, /, format_string=None):
    """
    Configurable logger. When you click on 'logger' parameter in other
    functions, PyCharm will show a dropdown with both logger definitions.
    """
    return f"Logger[{log_level}]"


# Example 5: Complex dependency chain
@injected
def process_data(
    database_connection,  # Click to navigate to @instance database_connection
    logger,  # Click to see dropdown with multiple logger definitions
    user_repository,  # Click to navigate to @instance user_repository
    /,
    data,
):
    """Process data using various dependencies."""
    logger.info("Processing data")
    # Fetch and process users
    user_repository.get_all()
    return f"Processed {len(data)} items"


# Example 6: Click on parameter usage in function body
@injected
def api_handler(database_connection, logger, /, request):
    """
    You can also click on parameter names when they're used
    in the function body to navigate to their definitions.
    """
    # Click on 'logger' below to navigate
    logger.info(f"Handling request: {request}")

    # Click on 'database_connection' below to navigate
    result = database_connection.query("SELECT * FROM users")

    return result
