from pinjected import injected, instance


# Mock functions/classes for examples
def format_data(data, fmt):
    return f"{data} in {fmt}"


def process(k1, k2):
    return k1, k2


class Database:
    def __init__(self, host, port):
        self.host = host
        self.port = port


@injected
def process_data(logger, transformer, data):
    # Without slash, ALL args (logger, transformer, data) are runtime args
    # This means NO dependencies will be injected!
    logger.info("Processing data")
    return transformer.process(data)


@injected
def analyze_results(database, cache, analyzer, results):
    # Without slash, these are ALL runtime args - no injection
    cache.set("key", results)
    return analyzer.analyze(results)


@injected
async def a_fetch_data(client, a_prepare_dataset, input_path):
    # Async with no slash - all args are runtime args
    dataset = a_prepare_dataset(input_path)
    return await client.fetch(dataset)


@injected
def only_runtime_args(input_data, output_format):
    # Even though these don't look like dependencies,
    # without slash they're runtime args (which they already would be)
    return format_data(input_data, output_format)


# Good examples - with slash
@injected
def good_process_data(logger, transformer, /, data):
    # Good - slash properly separates dependencies from runtime args
    logger.info("Processing data")
    return transformer.process(data)


@injected
def only_dependencies(logger, database, /):
    # Good - only dependencies, no runtime args
    logger.info("Initialized")
    return database.connect()


@injected
async def a_complex_handler(
    logger, cache, a_fetch_data, a_process_data, /, request_id: str, options: dict
):
    # Good - multiple dependencies and runtime args properly separated
    data = await a_fetch_data(request_id)
    return await a_process_data(data, options)


# Edge cases
@injected
def no_args():
    # No arguments at all - should not trigger
    return "result"


@injected
def keyword_only_args(*, key1, key2):
    # Keyword-only args without slash - should trigger
    return process(key1, key2)


@injected
def single_arg(logger):
    # Even single arg needs slash if it's meant to be injected
    logger.info("Hello")
    return True


# Not @injected - should be ignored
def regular_function(logger, data):
    # Not @injected, no slash needed
    return data


@instance
def database_connection(host, port):
    # @instance functions don't need slash
    return Database(host, port)
