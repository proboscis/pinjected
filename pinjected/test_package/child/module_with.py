
from pinjected import instances, injected

with instances(x=10):
    y = injected('x')
    with instances(y=20):
        z = injected('y')
    with instances(x=100):
        z2 = y

default_design = instances()

__meta_design__ = instances(
    default_design_paths=['pinjected.test_package.child.module_with.default_design'],
    overrides=instances()
)
