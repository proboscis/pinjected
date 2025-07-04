"""Example file with various @instance decorator violations."""

from pinjected import instance


# PINJ001: Bad instance naming (verb forms)
@instance
def get_database():
    """This should be 'database' not 'get_database'."""
    return Database()  # noqa: F821

@instance
def create_connection():
    """This should be 'connection' not 'create_connection'."""
    return Connection()  # noqa: F821

@instance
def setup_cache():
    """This should be 'cache' not 'setup_cache'."""
    return Cache()  # noqa: F821

# PINJ002: Instance functions with default arguments
@instance
def redis_client(host="localhost", port=6379):
    """Instance functions should not have default arguments."""
    return RedisClient(host, port)  # noqa: F821

@instance
def logger(level="INFO", format=None):
    """Configuration should be in design(), not defaults."""
    return Logger(level, format)  # noqa: F821

# PINJ003: Async instance with a_ prefix
@instance
async def a_database_connection():
    """Async @instance should not have a_ prefix."""
    return await create_async_connection()  # noqa: F821

@instance
async def a_message_queue():
    """The a_ prefix is only for @injected functions."""
    return await create_queue()  # noqa: F821

# PINJ004: Direct instance calls
def bad_initialization():
    # These are all wrong - direct calls to @instance
    db = get_database()  # ❌ Direct call
    conn = create_connection()  # ❌ Direct call
    cache = setup_cache()  # ❌ Direct call
    return db, conn, cache

# More PINJ004 violations
global_db = get_database()  # ❌ Module-level direct call
result = create_connection().execute("SELECT 1")  # ❌ Chained call