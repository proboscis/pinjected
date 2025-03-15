import asyncio

from pinjected import design, destructors
from pinjected.v2.async_resolver import AsyncResolver

test_design = design(
    x='x',
    y='y'
) + destructors(
    x=lambda: lambda x: print(f"destroying {x}")
)


def test_destruction_runs():
    res = AsyncResolver(test_design)
    assert asyncio.run(res['x']) == 'x'
    assert asyncio.run(res.destruct()) == [None]


