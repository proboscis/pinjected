from pinjected import injected, instance


@injected
async def print(logger, /, message):
    """Bad: shadows built-in 'print' (even as async)"""
    await logger.log(message)


@instance
async def list():
    """Bad: shadows built-in 'list' (even as async)"""
    return []
