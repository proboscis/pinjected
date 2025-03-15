import asyncio
import inspect
import pytest

from pinjected import design, Injected, injected
from pinjected.di.design_interface import DESIGN_OVERRIDES_STORE, DesignOverrideContext, DesignOverridesStore
from pinjected.module_var_path import ModuleVarPath
from pinjected.run_helpers.run_injected import run_injected
from pinjected.v2.async_resolver import AsyncResolver


def test_ovr_context():
    global x, y
    cxt1 = DesignOverrideContext(design(), inspect.currentframe())
    x = injected('hello')
    cxt2 = DesignOverrideContext(design(), inspect.currentframe())
    y = injected('world')
    mvps2 = cxt2.exit(inspect.currentframe())
    mvps1 = cxt1.exit(inspect.currentframe())
    print(mvps2)
    print(mvps1)


def test_ovr_store():
    global x, y
    store = DesignOverridesStore()
    store.add(inspect.currentframe(), design())
    x = injected('hello')
    store.add(inspect.currentframe(), design())
    y = injected('world')
    print(store)
    store.pop(inspect.currentframe())
    assert len(store.bindings) == 1
    store.pop(inspect.currentframe())
    assert len(store.bindings) == 2



def test_with_design(override_store_isolation):
    """
    Test nested design contexts with store isolation.
    
    Uses override_store_isolation fixture to ensure test has a clean store state.
    """
    global x, y, DESIGN_OVERRIDES_STORE
    with design(bind='level1', group='l1'):
        x = injected('hello')
        with design(bind='level2'):
            y = injected('world')
    assert len(DESIGN_OVERRIDES_STORE.bindings) == 2

    def resolve(path, key):
        d = DESIGN_OVERRIDES_STORE.bindings[path]
        return asyncio.run(AsyncResolver(d).provide(key))

    assert resolve(ModuleVarPath('test.test_with_block.y'), 'bind') == 'level2'
    assert resolve(ModuleVarPath('test.test_with_block.x'), 'bind') == 'level1'
    assert resolve(ModuleVarPath('test.test_with_block.y'), 'group') == 'l1'
    assert resolve(ModuleVarPath('test.test_with_block.x'), 'group') == 'l1'


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
