import asyncio

from pinjected import injected, instance


@injected
async def process_data(database, /):
    """Bad: async @injected should have a_ prefix"""
    await asyncio.sleep(0.1)
    return database


@injected
async def a_fetch_data(database, /):
    """Good: async @injected with a_ prefix"""
    await asyncio.sleep(0.1)
    return database


@instance
async def database():
    """Good: async @instance should not have a_ prefix"""
    return {"connected": True}
