import asyncio

from pinjected import design, Design
from pinjected.di.design import AddSummary, AddTags
from pinjected.pinjected_logging import logger

from pinjected.v2.async_resolver import AsyncResolver


def test_add_metadata():
    d = design()
    d += AddSummary("This is a test")
    d += AddTags("tag1")

    def get_metadata(__design__:Design):
        for d in __design__.dfs_design():
            logger.info(d)

    asyncio.run(AsyncResolver(d).provide(get_metadata))