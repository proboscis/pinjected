import asyncio

from pinjected import injected,design,instance,IProxy, Injected
from pinjected.di.design_interface import DESIGN_OVERRIDES_STORE
from pinjected.di.util import instances, providers
from pinjected.test_helper.test_runner import test_current_file

design01 = instances(name='design01')
design02 = design01 + instances(name='design02')
a = Injected.pure('a')
b = Injected.pure('b')



@instance
def test_viz_target(a, b):
    return a + b


@injected
def test_function(a, b):
    pass


@instance
def test_function2(a, /, b):
    pass

@instance
async def test_long_test():
    await asyncio.sleep(5)




variable_x: IProxy = injected('x')
variable_y: Injected = injected('y')


viz_target_design = providers(
    a=a,
    b=b
)
test_runnable = Injected.pure("hello world")



@instance
def test_always_failure():
    raise RuntimeError("This is always failure")

@instance
def test_missing_deps(missing_dep):
    return missing_dep

fail = test_always_failure
x = injected('x')
@injected
def iadd(x, y):
    return x + y
test_deep_ast_error:IProxy =  iadd(x, iadd(x, iadd(x,fail)))



with design(
        c="c"
):
    test_c = injected('c')
    with design(
        c="cc"
    ):
        test_cc = injected('c')

run_test:IProxy = test_current_file()

__meta_design__ = instances(
    overrides=design(
        a="a",
        b="b",
        x="x",
    ),
    name="test_package.child.module1",
)
