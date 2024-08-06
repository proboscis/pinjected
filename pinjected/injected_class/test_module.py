class PClassExample:
    _dep1: str
    _dep2: str
    a: str
    b: int
    c: float

    def _method(self):
        return (self.a, self.b, self.c)

    async def simple_method(self, x):
        return x

    async def method_with_dep1(self, x):
        return self._dep1, x

    async def method1(self, x):
        def test_inner():
            return self.a + str(self.b) + str(self.c)

        return self.a + str(self.b) + str(self.c) + x

    async def method2(self, y):
        return self._dep1 * y + str(self.c)


"""
Now this class works, 
but the fact we can't use a sync function
really limits its usage..
can i do something to this?

The problem is the dynamic dependency resolution.
since the resolver is async, the dynamic resolution must be async.
Can we somehow make the resolution in sync function?

how does nest_asyncio solving this task?

The only solution is to make resolver sync.
However, in that case, async dependencies cannot be automatically awaited.


"""

class PClassUser:
    dep: PClassExample

    async def do_something(self, x):
        await self.dep.method_with_dep1(x)
