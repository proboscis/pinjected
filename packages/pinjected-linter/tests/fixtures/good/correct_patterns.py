"""Example file demonstrating correct Pinjected patterns."""

from pinjected import instance, injected, design, IProxy

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
    return await create_redis_connection()

@instance
async def message_queue():
    """Correct: Pinjected handles async automatically."""
    return await create_queue()

# Good @injected patterns with proper dependency declaration
@injected
def process_workflow(
    logger,
    database,
    process_data,  # Declared dependency
    validate_data,  # Declared dependency
    /,
    input_data
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
    logger,
    a_fetch_data,  # Async dependency declared
    a_process_data,  # Async dependency declared
    /,
    resource_id: str
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
def initialize_services(logger, database, cache, queue, /):
    """Correct: all dependencies, slash at end for clarity."""
    logger.info("Initializing all services")
    return {"db": database, "cache": cache, "queue": queue}