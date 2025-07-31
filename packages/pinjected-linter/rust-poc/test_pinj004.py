from pinjected import design, injected, instance


@instance
def database():
    """An instance function"""
    return {"host": "localhost"}


@instance
def logger():
    """Another instance function"""
    return "logger"


def regular_function():
    """Not decorated - can call instance functions"""
    db = database()  # Bad: direct call to @instance
    log = logger()  # Bad: direct call to @instance
    return db, log


@injected
def process_data(database, logger, /):
    """Good: uses instances as dependencies"""
    logger.info("Processing...")
    return database


# In design context - should be OK
app = design(
    database=database(),  # OK: inside design()
    logger=logger(),  # OK: inside design()
)

# Nested design calls
complex_app = design(
    base=design(
        db=database(),  # OK: nested design()
    ),
    log=logger(),  # OK: in design()
)

# Bad: Direct calls outside design
db_direct = database()  # Bad: direct call
log_direct = logger()  # Bad: direct call

# Complex expressions with calls
result = {"db": database(), "log": logger()}  # Bad: both calls
items = [database(), logger()]  # Bad: both calls


# Test @instance(callable=True) - these should NOT trigger PINJ004
@instance(callable=True)
def event_handler_factory(logger, /):
    """Returns a callable that should be called directly"""

    def handle_event(event):
        logger.info(f"Handling: {event}")
        return event

    return handle_event


@instance(callable=True)
async def async_callback_factory(logger, /):
    """Async version that returns a callable"""

    async def callback(data):
        logger.info(f"Processing: {data}")
        return data

    return callback


# These direct calls should be allowed
handler = event_handler_factory()  # OK: @instance(callable=True)
async_handler = async_callback_factory()  # OK: @instance(callable=True)

# Using the returned callables - these are the actual function calls
result1 = handler("test event")  # OK: calling the returned function
# result2 = await async_handler("test data")  # OK: calling the returned async function


# Mix of regular @instance and @instance(callable=True)
@injected
def mixed_usage(database, event_handler_factory, /):
    """Good: both used as dependencies"""
    handler = event_handler_factory  # Note: not calling it here
    return database, handler


# Still bad - regular @instance functions
another_db = database()  # Bad: regular @instance
