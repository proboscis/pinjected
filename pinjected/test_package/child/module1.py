from pinjected import Injected, injected, instance
from pinjected.di.util import instances, providers

__meta_design__ = instances(
    name="test_package.child.module1",
    default_design_paths=[
        "pinjected.test_package.child.module1.design01"
    ]
)

design01 = instances(name='design01')
design02 = design01 + instances(name='design02')
a = Injected.pure('a')
b = Injected.pure('b')


def injected(f):
    return f


@instance
def test_viz_target(a, b):
    return a + b


@injected
def test_function(a, b):
    pass


@injected
def test_function2(a, /, b):
    pass



viz_target_design = providers(
    a=a,
    b=b
)
test_runnable = Injected.pure("hello world")
