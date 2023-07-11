from pinject_design import Injected
from pinject_design.di.util import instances

__meta_design__ = instances(
    name="test_package.child.module1"
)
test_runnable = Injected.pure("hello world")
