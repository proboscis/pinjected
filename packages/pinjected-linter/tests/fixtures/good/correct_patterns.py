"""Example file demonstrating correct Pinjected patterns."""

from pinjected import IProxy, design, injected, instance


# Mock classes for testing
class Database:
    def save(self, data):
        pass

    def query(self, sql):
        pass


class CacheManager:
    pass


class Config:
    pass


class RedisConnection:
    def __init__(self, host, port):
        pass


class MessageQueue:
    def __init__(self, capacity):
        pass


class Service:
    pass


class Factory:
    pass


class Component:
    pass


class AsyncClient:
    pass


# Mock objects for testing
class Trainer:
    def train(self, model):
        pass


class Pipeline:
    def run(self):
        pass


trainer = Trainer()
pipeline = Pipeline()
model = object()


# Good @instance patterns - noun forms
@instance
def database():
    """Correct: noun form, no verb."""
    return Database()


@instance
def cache_manager():
    """Correct: descriptive noun."""
    return CacheManager()


@instance
def configuration():
    """Correct: what is provided, not what to do."""
    return Config()


# Good async @instance - no a_ prefix
@instance
async def redis_connection():
    """Correct: async instance without a_ prefix."""
    # Creating connection object directly, not calling external function
    return RedisConnection(host="localhost", port=6379)


@instance
async def message_queue():
    """Correct: Pinjected handles async automatically."""
    # Direct instantiation, no side effects
    return MessageQueue(capacity=1000)


# Good @injected patterns with proper dependency declaration
@injected
def process_workflow(
    logger: IProxy,
    database: IProxy,
    process_data,  # Declared dependency
    validate_data,  # Declared dependency
    /,
    input_data,
):
    """Correct: all @injected dependencies declared."""
    processed = process_data(input_data)
    validated = validate_data(processed)
    database.save(validated)
    logger.info("Workflow complete")
    return validated


# Good async @injected with a_ prefix
@injected
async def a_fetch_and_process(
    logger: IProxy,
    a_fetch_data,  # Async dependency declared
    a_process_data,  # Async dependency declared
    /,
    resource_id: str,
):
    """Correct: async @injected with a_ prefix and declared deps."""
    data = await a_fetch_data(resource_id)
    result = await a_process_data(data)
    logger.info(f"Processed resource {resource_id}")
    return result


# Good use of design() instead of direct calls
base_config = design(
    database=database,  # ✅ Reference, not call
    cache=cache_manager,  # ✅ Reference, not call
    config=configuration,  # ✅ Reference, not call
)

# Good - using design() for configuration
production_config = base_config + design(
    database=database,  # Can override
    cache_ttl=3600,  # Configuration values
    debug=False,
)

# Good entry point with IProxy annotation
run_training: IProxy = trainer.train(model)
execute_pipeline: IProxy = pipeline.run()


# Good - all dependencies, no runtime args (slash optional but good practice)
@injected
def initialize_services(
    logger: IProxy, database: IProxy, cache: IProxy, queue: IProxy, /
):
    """Correct: all dependencies, slash at end for clarity."""
    logger.info("Initializing all services")
    return {"db": database, "cache": cache, "queue": queue}
