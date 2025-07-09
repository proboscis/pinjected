"""Test file for PINJ031: No injected() calls inside @instance/@injected functions"""

from pinjected import injected, instance


# BAD: Calling injected() inside @injected function
@injected
def my_service(config, db):
    # This is wrong - injected() should not be called inside @injected
    logger = injected()  # PINJ031
    return {"config": config, "db": db, "logger": logger}


# BAD: Calling injected() inside @instance function
@instance
def database_client(config):
    # This is wrong - injected() should not be called inside @instance
    pool = injected()  # PINJ031
    return DatabaseClient(config["db_url"], pool)


# BAD: Calling pinjected.injected() with module prefix
@injected
def api_handler(auth, cache):
    import pinjected

    # This is wrong - even with module prefix
    metrics = pinjected.injected()  # PINJ031
    return {"auth": auth, "cache": cache, "metrics": metrics}


# BAD: Multiple injected() calls
@injected
def complex_service(config):
    logger = injected()  # PINJ031
    db = injected()  # PINJ031
    cache = injected()  # PINJ031
    return ComplexService(config, logger, db, cache)


# BAD: injected() in nested function inside @injected
@injected
def outer_service(config):
    def inner_function():
        # Still wrong even in nested function
        logger = injected()  # PINJ031
        return logger

    return {"config": config, "inner": inner_function}


# BAD: injected() in async @injected function
@injected
async def async_service(config):
    logger = injected()  # PINJ031
    return await process(config, logger)


# BAD: injected() in async @instance function
@instance
async def async_client(config):
    pool = injected()  # PINJ031
    return await create_client(config, pool)


# GOOD: Normal function (not decorated) can call injected()
def regular_function():
    # This is fine - not inside @injected/@instance
    logger = injected()
    return logger


# GOOD: Using dependencies properly in @injected
@injected
def proper_service(logger, config, db):
    # logger is a dependency, not called with injected()
    return {"config": config, "db": db, "logger": logger}


# GOOD: Using dependencies properly in @instance
@instance
def proper_client(pool, config):
    # pool is a dependency, not called with injected()
    return DatabaseClient(config["db_url"], pool)


# GOOD: With noqa comment
@injected
def service_with_noqa(config):
    logger = injected()
    return {"config": config, "logger": logger}


# Edge case: injected as a variable name (should not trigger)
@injected
def service_with_var(config):
    injected = "not the function"  # This is just a variable
    return {"config": config, "value": injected}


# Edge case: Different function named injected (should not trigger)
def my_injected():
    return "custom"


@injected
def service_calling_custom(config):
    value = my_injected()  # Different function, not pinjected.injected
    return {"config": config, "value": value}


class DatabaseClient:
    def __init__(self, url, pool):
        self.url = url
        self.pool = pool


class ComplexService:
    def __init__(self, config, logger, db, cache):
        self.config = config
        self.logger = logger
        self.db = db
        self.cache = cache


async def process(config, logger):
    return {"processed": True}


async def create_client(config, pool):
    return DatabaseClient(config["url"], pool)
