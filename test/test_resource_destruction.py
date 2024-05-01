import asyncio

from pinjected import *

design = instances(
    x='x',
    y='y'
) + destructors(
    x=lambda: lambda x: print(f"destroying {x}")
)


def test_destruction_runs():
    res = design.to_resolver()
    assert asyncio.run(res['x']) == 'x'
    assert asyncio.run(res.destruct()) == [None]
