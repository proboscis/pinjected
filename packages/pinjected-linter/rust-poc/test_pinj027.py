"""Test file for PINJ027: No nested @injected functions"""

from pinjected import injected
from typing import Protocol, Any


# ❌ Incorrect: Nested @injected function
@injected
def outer_function(database, /, user_id: str):
    # PINJ027: @injected function 'inner_processor' cannot be defined inside @injected function 'outer_function'
    @injected
    def inner_processor(logger, /, data: dict):
        logger.info(f"Processing: {data}")
        return process(data)

    user = database.get_user(user_id)
    return inner_processor(user.data)


# ❌ Incorrect: Nested async @injected
@injected
async def a_test_v3_implementation(
    design,  # This is also wrong - design should not be a dependency
    logger,
    /,
    sketch_path: str,
) -> dict:
    # PINJ027: Nested @injected function
    @injected
    async def a_tracking_sketch_to_line_art(
        a_auto_cached_sketch_to_line_art: Any, /, sketch_path: str
    ) -> dict:
        return await a_auto_cached_sketch_to_line_art(sketch_path=sketch_path)

    # This pattern indicates misunderstanding of pinjected's design
    result = await a_tracking_sketch_to_line_art(sketch_path=sketch_path)
    return result


# ❌ Incorrect: Nested within conditional
@injected
def configurable_processor(config, /, data: str):
    if config.debug:
        # PINJ027: Even inside conditionals, nested @injected is forbidden
        @injected
        def debug_processor(logger, /, item):
            logger.debug(f"Debug: {item}")
            return item

        return debug_processor(data)
    return data


# ✅ Correct: Define protocols and functions at module level
class ProcessorProtocol(Protocol):
    def __call__(self, data: dict) -> dict: ...


class TrackingLineArtProtocol(Protocol):
    async def __call__(self, sketch_path: str) -> dict: ...


# ✅ Correct: Module-level @injected functions
@injected(protocol=ProcessorProtocol)
def inner_processor(logger, /, data: dict) -> dict:
    logger.info(f"Processing: {data}")
    return process(data)


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


# ✅ Correct: Regular functions inside @injected are OK
@injected
def process_data(logger, /, items: list):
    # Regular function (not @injected) is fine
    def helper(item):
        return item * 2

    return [helper(item) for item in items]
