"""Test file for PINJ034: No lambda or non-decorated functions in design()"""

from pinjected import design, injected, instance


# Placeholder classes for examples
class Logger:
    pass


class DebugLogger(Logger):
    pass


class ProductionLogger(Logger):
    pass


class DatabaseConnection:
    def __init__(self, config):
        self.config = config


class Client:
    def __init__(self, url):
        self.url = url


class UserService:
    pass


# ❌ Incorrect: Lambda function in design subscript assignment
with design() as d:
    # PINJ034: Lambda function cannot be assigned to design context 'd'
    d["get_config"] = lambda: {"debug": True}

    # PINJ034: Lambda with parameters
    d["create_client"] = lambda config: Client(config["url"])


# ❌ Incorrect: Lambda in direct assignment
config = {"host": "localhost"}

# PINJ034: Lambda function in design()
db_design = design(
    database=lambda: DatabaseConnection({"host": "localhost"}),
    cached_db=lambda: DatabaseConnection(config),  # Lambda with captured variable
)


# ❌ Incorrect: Non-decorated function
def create_logger():
    """Regular function without decorator."""
    return Logger()


def get_user_service():
    """Another regular function."""
    return UserService()


with design() as d:
    # PINJ034: Function 'create_logger' is not decorated
    d["logger"] = create_logger

    # PINJ034: Function 'get_user_service' is not decorated
    d["user_service"] = get_user_service


# ❌ Incorrect: Inline function definition
with design() as d:

    def inline_factory():  # Not decorated
        return UserService()

    # PINJ034: Function 'inline_factory' is not decorated
    d["user_service"] = inline_factory


# ❌ Incorrect: Conditional lambda assignments
debug_mode = True

with design() as d:
    if debug_mode:
        # PINJ034: Lambda in conditional
        d["logger"] = lambda: DebugLogger()
    else:
        # PINJ034: Lambda in else branch
        d["logger"] = lambda: ProductionLogger()


# ❌ Incorrect: Lambda in design override
@injected
def original_config():
    return {"debug": False}


# Base design
base = design(config=original_config)

# PINJ034: Lambda in override design
overridden = base + design(
    config=lambda: {"debug": True}  # Lambda function
)


# ✅ Correct: Use @injected decorator
@injected
def get_config():
    return {"debug": True}


@injected
def create_client(config, /):
    return Client(config["url"])


with design() as d:
    d["config"] = get_config  # OK: decorated function
    d["client"] = create_client  # OK: decorated function


# ✅ Correct: Use @instance decorator
@instance
def database_connection(config, /):
    return DatabaseConnection(config)


@instance
def logger():
    return Logger()


service_design = design(
    database=database_connection,  # OK: decorated function
    logger=logger,  # OK: decorated function
)


# ✅ Correct: Conditional dependencies with factory pattern
@instance
def debug_logger():
    return DebugLogger()


@instance
def production_logger():
    return ProductionLogger()


@injected
def logger_factory(config, debug_logger, production_logger, /):
    return debug_logger if config["debug"] else production_logger


logging_design = design(
    logger=logger_factory,
    debug_logger=debug_logger,
    production_logger=production_logger,
)


# ✅ Correct: Override with decorated function
@injected
def test_config():
    return {"debug": True}


# Compose designs to override
test_design = design(config=original_config) + design(config=test_config)


# ✅ Correct: Direct design composition
app_design = design(
    config=get_config, database=database_connection, logger=logger, client=create_client
)
