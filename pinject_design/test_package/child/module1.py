from pinject_design import Injected
from pinject_design.di.util import instances

__meta_design__ = instances(
    name="test_package.child.module1"
)

design01 = instances(name='design01')
design02 = design01 + instances(name='design02')
test_runnable = Injected.pure("hello world")
