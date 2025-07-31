import asyncio

from pinjected import injected, instance


@instance
async def a_database():
    """Bad: async @instance should not have a_ prefix"""
    return {"connected": True}


@instance
async def database():
    """Good: async @instance without a_ prefix"""
    return {"connected": True}


@injected
async def a_process_data(database, /):
    """Good: async @injected should have a_ prefix"""
    await asyncio.sleep(0.1)
    return database
