"""Test file for PINJ028: No design() usage inside @injected functions"""

from pinjected import injected, design, instance
import pinjected
from typing import Protocol


# ❌ Incorrect: Using design() inside @injected
@injected
async def a_test_v3_implementation(logger, /, sketch_path: str) -> dict:
    # PINJ028: design() cannot be used inside @injected functions
    with design() as d:

        @injected
        async def a_tracking_sketch_to_line_art(
            a_auto_cached_sketch_to_line_art, /, sketch_path: str
        ) -> dict:
            return await a_auto_cached_sketch_to_line_art(sketch_path=sketch_path)

        d.provide(a_tracking_sketch_to_line_art)

    # This pattern shows confusion about pinjected's architecture
    result = await a_tracking_sketch_to_line_art(sketch_path=sketch_path)
    return result


# ❌ Incorrect: design() with pinjected module
@injected
def configure_dynamically(config_loader, /, env: str):
    config = config_loader.load(env)

    # PINJ028: Trying to configure dependencies at runtime
    with pinjected.design() as d:
        if config.use_mock:
            d.provide(mock_database)
        else:
            d.provide(real_database)

    # This doesn't work - design() is for configuration, not runtime


# ❌ Incorrect: design() in conditional
@injected
def dynamic_config(env_var, /, mode: str):
    if mode == "test":
        # PINJ028: Even inside conditionals, design() is forbidden
        with design() as d:
            d.provide(test_database)
            return d.to_graph()
    else:
        return production_graph()


# ✅ Correct: design() outside of @injected functions
def configure_app(use_mock: bool = False):
    with design() as d:
        d.provide(a_tracking_sketch_to_line_art)
        d.provide(a_auto_cached_sketch_to_line_art)

        # Configuration decisions happen here, not at runtime
        if use_mock:
            d.provide(mock_database)
        else:
            d.provide(real_database)

    return d.to_graph()


# ✅ Correct: Define protocols and functions at module level
class LineArtProtocol(Protocol):
    async def __call__(self, sketch_path: str) -> dict: ...


class DatabaseProtocol(Protocol):
    def query(self, sql: str) -> list: ...


# ✅ Correct: Module-level @injected function
@injected(protocol=LineArtProtocol)
async def a_tracking_sketch_to_line_art(
    a_auto_cached_sketch_to_line_art, /, sketch_path: str
) -> dict:
    # No await needed when calling injected dependencies!
    return a_auto_cached_sketch_to_line_art(sketch_path=sketch_path)


# ✅ Correct: Use dependencies without design()
@injected
async def a_test_v3_implementation_correct(
    a_tracking_sketch_to_line_art: LineArtProtocol,  # Inject as dependency
    logger,
    /,
    sketch_path: str,
) -> dict:
    # Call the injected dependency directly
    result = a_tracking_sketch_to_line_art(sketch_path=sketch_path)
    return result


# ✅ Correct: Use @instance for conditional dependencies
@instance
def database(config) -> DatabaseProtocol:
    if config.use_mock:
        return MockDatabase()
    else:
        return RealDatabase(config.db_url)


# ✅ Correct: Regular with statements are fine
@injected
def file_processor(file_system, /, path: str):
    # Regular context managers are OK
    with open(path) as f:
        content = f.read()

    with file_system.lock():
        result = process(content)

    return result
