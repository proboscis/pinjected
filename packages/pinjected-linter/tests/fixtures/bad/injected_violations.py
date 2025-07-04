"""Example file with @injected decorator violations."""

from pinjected import injected

# Define the functions that will be called without declaration
@injected
async def a_fetch_data(client, /, resource_id):
    return await client.fetch(resource_id)

@injected  
async def a_process_data(processor, /, data):
    return await processor.process(data)

# PINJ008: Calling @injected functions without declaring them as dependencies
@injected
def process_data(transformer, /):
    return transformer.process()

@injected
def validate_data(validator, /):
    return validator.validate()

@injected
def bad_workflow(logger, /):
    # These will cause NameError at runtime!
    data = process_data("input")  # ❌ process_data not declared
    valid = validate_data(data)  # ❌ validate_data not declared
    return logger.log(valid)

@injected
async def a_bad_async_workflow(database, /):
    # Async functions have the same issue
    data = await a_fetch_data()  # ❌ a_fetch_data not declared
    result = await a_process_data(data)  # ❌ a_process_data not declared
    return await database.save(result)

# PINJ015: Missing slash - but this is tricky!
# This might be a false positive if all args are dependencies
@injected
def maybe_missing_slash(logger, database, analyzer, input_data):
    """Is input_data a dependency or runtime arg? Can't tell!"""
    # If input_data is a runtime arg, this needs a slash
    # If it's a dependency, this is fine
    return analyzer.analyze(input_data)

# Clearly missing slash - mixing deps and runtime args
@injected
def definitely_missing_slash(logger, database, user_id, request_data):
    """user_id and request_data look like runtime args."""
    # This pattern suggests runtime args mixed with dependencies
    user = database.get_user(user_id)
    return logger.log(f"Processing request for {user}")

# PINJ015: No slash means ALL args are runtime args (NOT dependencies!)
@injected
def all_dependencies(logger, database, cache, message_queue):
    """Without slash, these are ALL runtime args - NO injection happens!"""
    # This is BAD - without slash, you'd need to pass all 4 args when calling
    logger.info("All systems connected")
    return True