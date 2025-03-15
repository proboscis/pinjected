from pinjected import injected, Injected, design, instance


@injected
async def function(dep, __resolver__, /, x: Injected, y: int, z):
    return (await __resolver__[x]) + y + z


def test_args_pure():
    x = Injected.pure('x').add_dynamic_dependencies('dyn_dep')

    d = design(
        dyn_dep="dyn",
        dep="hello"
    )

    # TODO add dynamic_dependencies

    called = function(x, "1", "2")
    assert d.provide(called) == 'x12', f"expected x12, got {d.provide(called)}"


def test_something():
    assert type(0) == int, "0 must be int"

@instance
def run_test(dep1,dep2):
    return 0


__meta_design__ = design()