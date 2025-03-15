
from pinjected import design, injected

with design(x=10):
    y = injected('x')
    with design(y=20):
        z = injected('y')
    with design(x=100):
        z2 = y

default_design = design()

__meta_design__ = design(
    default_design_paths=['pinjected.test_package.child.module_with.default_design'],
    overrides=design()
)
