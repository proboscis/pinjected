import inspect

from pinjected import instances, Injected, injected
from pinjected.di.design_interface import DESIGN_OVERRIDES_STORE, DesignOverrideContext
from pinjected.module_var_path import ModuleVarPath
from pinjected.run_helpers.run_injected import run_injected


def test_ovr_context():
    global x, y
    cxt1 = DesignOverrideContext(instances(), inspect.currentframe())
    x = injected('hello')
    cxt2 = DesignOverrideContext(instances(), inspect.currentframe())
    y = injected('world')
    mvps2 = cxt2.exit(inspect.currentframe())
    mvps1 = cxt1.exit(inspect.currentframe())
    print(mvps2)
    print(mvps1)


def test_ovr_store():
    global x, y
    DESIGN_OVERRIDES_STORE.add(inspect.currentframe(), instances())
    x = injected('hello')
    DESIGN_OVERRIDES_STORE.add(inspect.currentframe(), instances())
    y = injected('world')
    print(DESIGN_OVERRIDES_STORE)
    DESIGN_OVERRIDES_STORE.pop(inspect.currentframe())
    assert len(DESIGN_OVERRIDES_STORE.bindings) == 1
    DESIGN_OVERRIDES_STORE.pop(inspect.currentframe())
    assert len(DESIGN_OVERRIDES_STORE.bindings) == 2


def test_with_design():
    global x, y
    with instances(bind='level1', group='l1'):
        x = injected('hello')
        with instances(bind='level2'):
            y = injected('world')
    assert len(DESIGN_OVERRIDES_STORE.bindings) == 2
    assert DESIGN_OVERRIDES_STORE.bindings[ModuleVarPath('test.test_with_block.y')].provide('bind') == 'level2'
    assert DESIGN_OVERRIDES_STORE.bindings[ModuleVarPath('test.test_with_block.x')].provide('bind') == 'level1'
    assert DESIGN_OVERRIDES_STORE.bindings[ModuleVarPath('test.test_with_block.y')].provide('group') == 'l1'
    assert DESIGN_OVERRIDES_STORE.bindings[ModuleVarPath('test.test_with_block.x')].provide('group') == 'l1'


def test_run_injected():
    y = run_injected(
        cmd='get',
        var_path='pinjected.test_package.child.module_with.y',
        return_result=True
    )
    assert y == 10, f"y is {y} instead of 10"
    z = run_injected(
        cmd='get',
        var_path='pinjected.test_package.child.module_with.z',
        return_result=True
    )
    assert z == 20, f"z is {z} instead of 20"
    z2 = run_injected(
        cmd='get',
        var_path='pinjected.test_package.child.module_with.z2',
        return_result=True
    )
    assert z2 == 100, f"z2 is {z2} instead of 100"
