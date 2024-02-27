from pinjected import instances, Injected, injected
from pinjected.di.design import DesignOverrideContext

with DesignOverrideContext(
        instances(x='hello'),
        callback=print,
        depth=0
):
    y = Injected.pure('great')
    z = injected('x') + "hello"
    with DesignOverrideContext(
            instances(x='world'),
            callback=print,
            depth=1
    ):
        z: Injected = injected('x') + "hello"

"""
store the changes..
"""
__meta_design__ = instances(
    default_design_paths=['test.test_with_block.test_design']
)
test_design = instances(
    x='default x'
)
