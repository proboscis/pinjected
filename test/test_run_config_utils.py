import sys
from pathlib import Path

from pinjected import *
from pinjected.helper_structure import MetaContext
from pinjected.ide_supports.create_configs import create_idea_configurations
from pinjected.run_helpers.run_injected import run_injected
from pinjected.v2.async_resolver import AsyncResolver

p_root = Path(__file__).parent.parent
TEST_MODULE = p_root/"pinjected/test_package/child/module1.py"
import pytest


@pytest.mark.asyncio
async def test_create_configurations():
    """Test configuration creation using the non-deprecated a_gather_bindings_with_legacy method."""
    from pinjected.ide_supports.default_design import pinjected_internal_design
    from pinjected.helper_structure import IdeaRunConfigurations
    
    # create_idea_configurationsの引数を正しく設定
    configs = create_idea_configurations(wrap_output_with_tag=False)
    
    # Using the non-deprecated a_gather_bindings_with_legacy method
    mc = await MetaContext.a_gather_bindings_with_legacy(p_root/"pinjected/ide_supports/create_configs.py")
    
    # Print diagnostic information for the new method
    print(f"Method trace count: {len(mc.trace)}")
    print(f"Method trace paths:")
    for i, var in enumerate(mc.trace):
        print(f"  {i}. {var.var_path}")
    
    # Test that we can access meta_config_value from __design__ (which overrides __meta_design__)
    dd = (await mc.a_final_design) + design(
        module_path=TEST_MODULE,
        interpreter_path=sys.executable
    ) + pinjected_internal_design + design(print_to_stdout=False)
    
    rr = AsyncResolver(dd)
    
    # Verify the design value before running the configurations
    meta_config_value = await rr.provide("meta_config_value")
    print(f"meta_config_value: {meta_config_value}")
    assert meta_config_value == "from_design", "Should get value from __design__"
    
    # Check that we have access to additional_config_value which is only in __design__
    additional_config_value = await rr.provide("additional_config_value")
    print(f"additional_config_value: {additional_config_value}")
    assert additional_config_value == "only_in_design", "Should have access to values only in __design__"
    
    # Now get the configuration result
    res = await rr[configs]
    
    # With print_to_stdout=False, we should get an actual result back
    assert res is not None, "Result should not be None with print_to_stdout=False"
    assert isinstance(res, IdeaRunConfigurations), "Result should be an IdeaRunConfigurations object"
    
    # Examine the configs dictionary
    config_dict = res.configs
    print(f"Configuration keys: {list(config_dict.keys())}")
    
    # Verify that test_runnable is in the configurations
    assert "test_runnable" in config_dict, "Should have configuration for test_runnable"
    
    # Verify expected keys are present (a, b, test_viz_target are in module1.py)
    expected_keys = ["a", "b", "test_viz_target"]
    for key in expected_keys:
        assert key in config_dict, f"Should have configuration for '{key}'"
    
    # Verify the structure of a configuration
    first_key = list(config_dict.keys())[0]
    first_config = config_dict[first_key][0]
    
    # Verify the configuration has all required fields
    assert hasattr(first_config, "name"), "Config should have a name"
    assert hasattr(first_config, "script_path"), "Config should have a script_path"
    assert hasattr(first_config, "interpreter_path"), "Config should have an interpreter_path"
    assert hasattr(first_config, "arguments"), "Config should have arguments"
    assert hasattr(first_config, "working_dir"), "Config should have a working_dir"
    
    
@pytest.mark.asyncio
async def test_create_configurations_legacy_comparison():
    """
    Legacy comparison test showing the differences between a_gather_from_path and a_gather_bindings_with_legacy.
    This test is kept for reference to understand the behavior of the deprecated method.
    """
    from pinjected.ide_supports.default_design import pinjected_internal_design
    from pinjected.helper_structure import IdeaRunConfigurations
    
    # Create configurations injected object
    configs = create_idea_configurations(wrap_output_with_tag=False)
    
    # Using the deprecated a_gather_from_path for comparison
    legacy_mc = await MetaContext.a_gather_from_path(p_root/"pinjected/ide_supports/create_configs.py")
    
    # Print diagnostic information for the legacy method
    print(f"Legacy method trace count: {len(legacy_mc.trace)}")
    print(f"Legacy method trace paths:")
    for i, var in enumerate(legacy_mc.trace):
        print(f"  {i}. {var.var_path}")
        
    # Using the non-deprecated a_gather_bindings_with_legacy method
    new_mc = await MetaContext.a_gather_bindings_with_legacy(p_root/"pinjected/ide_supports/create_configs.py")
    
    # Print diagnostic information for the new method
    print(f"New method trace count: {len(new_mc.trace)}")
    print(f"New method trace paths:")
    for i, var in enumerate(new_mc.trace):
        print(f"  {i}. {var.var_path}")
    
    # Create designs with both legacy and new methods
    legacy_dd = (await legacy_mc.a_final_design) + design(
        module_path=TEST_MODULE,
        interpreter_path=sys.executable
    ) + pinjected_internal_design + design(print_to_stdout=False)
    
    new_dd = (await new_mc.a_final_design) + design(
        module_path=TEST_MODULE,
        interpreter_path=sys.executable
    ) + pinjected_internal_design + design(print_to_stdout=False)
    
    # Create resolvers for both designs
    legacy_rr = AsyncResolver(legacy_dd)
    new_rr = AsyncResolver(new_dd)
    
    # Compare meta_config_value from both methods
    legacy_meta_value = await legacy_rr.provide("meta_config_value")
    new_meta_value = await new_rr.provide("meta_config_value")
    
    print(f"meta_config_value with legacy method: {legacy_meta_value}")
    print(f"meta_config_value with new method: {new_meta_value}")
    
    # Legacy method should get value from __meta_design__
    assert legacy_meta_value == "from_meta_design", "Legacy method should get value from __meta_design__"
    
    # New method should get value from __design__ which overrides __meta_design__
    assert new_meta_value == "from_design", "New method should get value from __design__"
    
    # Check if additional_config_value is accessible with each method
    try:
        legacy_add_value = await legacy_rr.provide("additional_config_value")
        print(f"additional_config_value with legacy method: {legacy_add_value}")
        legacy_has_additional = True
    except Exception as e:
        print(f"Legacy method can't access additional_config_value: {str(e)}")
        legacy_has_additional = False
    
    new_add_value = await new_rr.provide("additional_config_value")
    print(f"additional_config_value with new method: {new_add_value}")
    
    # Legacy method should not have access to values only in __design__
    assert not legacy_has_additional, "Legacy method should not have access to values only in __design__"
    
    # New method should have access to values only in __design__
    assert new_add_value == "only_in_design", "New method should have access to values only in __design__"
    
    # Run configurations using both methods
    legacy_res = await legacy_rr[configs]
    new_res = await new_rr[configs]
    
    # Both should return actual configuration objects (with print_to_stdout=False)
    assert legacy_res is not None and new_res is not None, "Both methods should return configuration objects"
    assert isinstance(legacy_res, IdeaRunConfigurations) and isinstance(new_res, IdeaRunConfigurations), \
        "Both methods should return IdeaRunConfigurations objects"
    
    # Both should generate identical configurations
    legacy_configs = legacy_res.configs
    new_configs = new_res.configs
    
    # Compare the keys first
    legacy_keys = set(legacy_configs.keys())
    new_keys = set(new_configs.keys())
    
    print(f"Legacy method configuration keys: {sorted(list(legacy_keys))}")
    print(f"New method configuration keys: {sorted(list(new_keys))}")
    
    # The key sets should be identical since they use the same module
    assert legacy_keys == new_keys, "Both methods should generate the same configuration keys"
    
    # Now do a deep comparison of the actual configuration contents
    print("Comparing individual configurations for each key...")
    for key in legacy_keys:
        legacy_items = legacy_configs[key]
        new_items = new_configs[key]
        
        # Check if the number of configurations for each key is the same
        assert len(legacy_items) == len(new_items), f"Key '{key}' has different number of configurations"
        
        # Compare each configuration item
        for i, (legacy_item, new_item) in enumerate(zip(legacy_items, new_items)):
            # Compare each field
            assert legacy_item.name == new_item.name, f"Configuration {i} for '{key}' has different name"
            assert legacy_item.script_path == new_item.script_path, f"Configuration {i} for '{key}' has different script_path"
            assert legacy_item.interpreter_path == new_item.interpreter_path, f"Configuration {i} for '{key}' has different interpreter_path"
            assert legacy_item.working_dir == new_item.working_dir, f"Configuration {i} for '{key}' has different working_dir"
            
            # For arguments, we need to compare the lists
            assert legacy_item.arguments == new_item.arguments, f"Configuration {i} for '{key}' has different arguments"
    
    print("All configurations identical between legacy and new method!")
            
    # The important difference is that the new method gets access to both __meta_design__ 
    # and __design__ attributes, with __design__ taking precedence, while maintaining
    # identical configuration generation


test_design = design(x=0)
test_var = Injected.by_name("x")



def test_run_injected():
    res = run_injected(
        "get",
        "pinjected.test_package.child.module1.test_runnable",
        "pinjected.test_package.child.module1.design01",
        return_result=True
    )
    print(res)
    assert res == "hello world"

def test_run_injected_with_handle():
    res = run_injected(
        "get",
        "pinjected.test_package.child.module1.test_runnable",
        "pinjected.test_package.child.module1.design03",
        return_result=True
    )
    print(res)
    assert res == "hello world"


def test_run_injected_exception_with_handle():
    with pytest.raises(Exception):
        res = run_injected(
            "get",
            "pinjected.test_package.child.module1.test_always_failure",
            "pinjected.test_package.child.module1.design03",
            return_result=True
        )