import asyncio

from pinjected import *
from pinjected.v2.resolver import AsyncResolver

design = instances(
    x='x',
    y='y'
) + destructors(
    x=lambda: lambda x: print(f"destroying {x}")
)


def test_destruction_runs():
    res = AsyncResolver(design)
    assert asyncio.run(res['x']) == 'x'
    assert asyncio.run(res.destruct()) == [None]


