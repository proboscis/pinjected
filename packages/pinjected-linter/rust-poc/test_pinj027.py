"""Test file for PINJ027: No nested @injected or @instance definitions"""

from pinjected import injected, instance
from typing import Protocol


# Placeholder definitions for test examples
def process(data):
    return data


class DatabaseConnection:
    pass


class CacheService:
    pass


class ErrorHandler:
    pass


# ❌ Incorrect: @injected inside regular function
def regular_function(user_id: str):
    # PINJ027: @injected function 'inner_processor' cannot be defined inside function 'regular_function'
    @injected
    def inner_processor(logger, /, data: dict):
        logger.info(f"Processing: {data}")
        return process(data)

    return inner_processor({})


# ❌ Incorrect: @instance inside class
class MyService:
    # PINJ027: @instance function 'database' cannot be defined inside class 'MyService'
    @instance
    def database(self, config, /):
        return DatabaseConnection(config)


# ❌ Incorrect: @injected inside method
class DataProcessor:
    def process_items(self, items):
        # PINJ027: @injected function 'item_handler' cannot be defined inside function 'process_items' inside class 'DataProcessor'
        @injected
        def item_handler(logger, /, item):
            logger.info(f"Processing item: {item}")
            return item * 2

        return [item_handler(item) for item in items]


# ❌ Incorrect: @instance inside async function
async def setup_services():
    # PINJ027: @instance function 'cache_service' cannot be defined inside function 'setup_services'
    @instance
    def cache_service(redis_config, /):
        return CacheService(redis_config)

    return cache_service()


# ❌ Incorrect: Nested within conditional
def configurable_processor(config, data: str):
    if config.debug:
        # PINJ027: Even inside conditionals, @injected is forbidden
        @injected
        def debug_processor(logger, /, item):
            logger.debug(f"Debug: {item}")
            return item

        return debug_processor(data)
    return data


# ❌ Incorrect: @instance in try block
def safe_setup():
    try:
        # PINJ027: @instance function 'error_handler' cannot be defined inside function 'safe_setup'
        @instance
        def error_handler(logger, /):
            return ErrorHandler(logger)

        return error_handler()
    except Exception:
        return None


# ✅ Correct: Define protocols and functions at module level
class ProcessorProtocol(Protocol):
    def __call__(self, data: dict) -> dict: ...


class TrackingLineArtProtocol(Protocol):
    async def __call__(self, sketch_path: str) -> dict: ...


# ✅ Correct: Module-level @injected and @instance functions
@injected(protocol=ProcessorProtocol)
def inner_processor(logger, /, data: dict) -> dict:
    logger.info(f"Processing: {data}")
    return process(data)


@instance
def database_connection(config, /):
    """Database connection defined at module level - correct."""
    return DatabaseConnection(config)


@injected(protocol=TrackingLineArtProtocol)
async def a_tracking_sketch_to_line_art(
    a_auto_cached_sketch_to_line_art, /, sketch_path: str
) -> dict:
    # No await needed when calling injected dependencies!
    return a_auto_cached_sketch_to_line_art(sketch_path=sketch_path)


# ✅ Correct: Inject dependencies properly
@injected
def outer_function_correct(
    database,
    inner_processor: ProcessorProtocol,  # Inject as dependency
    /,
    user_id: str,
):
    user = database.get_user(user_id)
    return inner_processor(user.data)


@injected
async def a_test_v3_implementation_correct(
    a_tracking_sketch_to_line_art: TrackingLineArtProtocol,  # Inject properly
    logger,
    /,
    sketch_path: str,
) -> dict:
    # Call the injected dependency - no await needed!
    result = a_tracking_sketch_to_line_art(sketch_path=sketch_path)
    return result


# ✅ Correct: Regular functions (without decorators) can be defined anywhere
def process_data(items: list):
    # Regular function (not @injected/@instance) is fine
    def helper(item):
        return item * 2

    return [helper(item) for item in items]


class ServiceManager:
    def initialize(self):
        # Regular helper function is OK
        def setup_logging():
            import logging

            return logging.getLogger(__name__)

        self.logger = setup_logging()


# ✅ Correct: Factory pattern for conditional dependencies
@injected
def debug_processor(logger, /, item):
    logger.debug(f"Debug: {item}")
    return item


@injected
def regular_processor(item):
    return item


@injected
def get_processor(config, debug_processor, regular_processor, /):
    """Select processor based on config."""
    return debug_processor if config.debug else regular_processor
