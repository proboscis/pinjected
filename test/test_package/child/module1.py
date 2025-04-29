from pinjected import Injected, IProxy, design

test_test_object:IProxy = Injected.pure('test')
test_c:IProxy = Injected.pure('c')
test_cc:IProxy = Injected.pure('cc')

__meta_design__ = design(
    name="test_package.child.module1"
)
