from pinjected import injected, instance


@instance
def database(host="localhost", port=5432):
    """Bad: has default arguments"""
    return {"host": host, "port": port}


@instance
def logger():
    """Good: no default arguments"""
    return "logger"


@injected
def process_data(database, logger, /, batch_size=100):
    """OK: @injected can have defaults after slash"""
    logger.info(f"Processing with batch_size={batch_size}")
    return database
