from pinjected import injected, instance


@instance
def dict():
    """Bad: shadows built-in 'dict'"""
    return {}


@instance
def config_dict():
    """Good: descriptive name that doesn't shadow built-in"""
    return {}


@injected
def open(file_handler, /, path):
    """Bad: shadows built-in 'open'"""
    return file_handler.open(path)


@injected
def open_file(file_handler, /, path):
    """Good: descriptive name that doesn't shadow built-in"""
    return file_handler.open(path)


@injected
async def a_print(logger, /, message):
    """Bad: shadows built-in 'print'"""
    await logger.log(message)


# Regular function (not decorated) - should NOT be flagged
def list():
    """OK: not decorated with @instance or @injected"""
    return []
