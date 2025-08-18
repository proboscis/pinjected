import sys
from pathlib import Path

import pytest

from pinjected import *
from pinjected.helper_structure import MetaContext
from pinjected.run_helpers.run_injected import run_injected
from pinjected.v2.async_resolver import AsyncResolver

p_root = Path(__file__).parent.parent
TEST_MODULE = p_root / "pinjected/test_package/child/module1.py"


@pytest.mark.asyncio
async def test_create_configurations():
    """Test configuration creation using the non-deprecated a_gather_bindings_with_legacy method."""
    from pinjected.helper_structure import IdeaRunConfigurations
    from pinjected.ide_supports.default_design import pinjected_internal_design

    # Using the non-deprecated a_gather_bindings_with_legacy method
    mc = await MetaContext.a_gather_bindings_with_legacy(
        p_root / "pinjected/ide_supports/create_configs.py"
    )

    # Print diagnostic information for the new method
    print(f"Method trace count: {len(mc.trace)}")
    print("Method trace paths:")
    for i, var in enumerate(mc.trace):
        print(f"  {i}. {var.var_path}")

    # Test that we can access meta_config_value from __design__ (which overrides __meta_design__)
    dd = (
        (await mc.a_final_design)
        + design(
            module_path=TEST_MODULE,
            interpreter_path=sys.executable,
            default_design_paths=[],  # Add required dependency
        )
        + pinjected_internal_design
        + design(print_to_stdout=False)
        + design(__pinjected__wrap_output_with_tag=False)  # Add this dependency
    )

    rr = AsyncResolver(dd)

    # Verify the design value before running the configurations
    meta_config_value = await rr.provide("meta_config_value")
    print(f"meta_config_value: {meta_config_value}")
    assert meta_config_value == "from_design", "Should get value from __design__"

    # Check that we have access to additional_config_value which is only in __design__
    additional_config_value = await rr.provide("additional_config_value")
    print(f"additional_config_value: {additional_config_value}")
    assert additional_config_value == "only_in_design", (
        "Should have access to values only in __design__"
    )

    # Now get the configuration result by resolving create_idea_configurations through the resolver
    res = await rr.provide("create_idea_configurations")

    # With print_to_stdout=False, we should get an actual result back
    assert res is not None, "Result should not be None with print_to_stdout=False"
    assert isinstance(res, IdeaRunConfigurations), (
        "Result should be an IdeaRunConfigurations object"
    )

    # Examine the configs dictionary
    config_dict = res.configs
    print(f"Configuration keys: {list(config_dict.keys())}")

    # Verify that test_runnable is in the configurations
    assert "test_runnable" in config_dict, "Should have configuration for test_runnable"

    # Verify expected keys are present (a, b, test_viz_target are in module1.py)
    # NOTE: test_viz_target should now work since we added DelegatedVar support
    expected_keys = ["a", "b", "test_viz_target"]
    for key in expected_keys:
        assert key in config_dict, f"Should have configuration for '{key}'"

    # Verify the structure of a configuration
    first_key = next(iter(config_dict.keys()))
    first_config = config_dict[first_key][0]

    # Verify the configuration has all required fields
    assert hasattr(first_config, "name"), "Config should have a name"
    assert hasattr(first_config, "script_path"), "Config should have a script_path"
    assert hasattr(first_config, "interpreter_path"), (
        "Config should have an interpreter_path"
    )
    assert hasattr(first_config, "arguments"), "Config should have arguments"
    assert hasattr(first_config, "working_dir"), "Config should have a working_dir"


# Legacy comparison test removed since __meta_design__ was removed from create_configs.py
# The main test_create_configurations already validates the functionality


test_design = design(x=0)
test_var = Injected.by_name("x")


def test_run_injected():
    res = run_injected(
        "get",
        "pinjected.test_package.child.module1.test_runnable",
        "pinjected.test_package.child.module1.design01",
        return_result=True,
    )
    print(res)
    assert res == "hello world"


def test_run_injected_with_handle():
    res = run_injected(
        "get",
        "pinjected.test_package.child.module1.test_runnable",
        "pinjected.test_package.child.module1.design03",
        return_result=True,
    )
    print(res)
    assert res == "hello world"


def test_run_injected_exception_with_handle():
    with pytest.raises(Exception):
        run_injected(
            "get",
            "pinjected.test_package.child.module1.test_always_failure",
            "pinjected.test_package.child.module1.design03",
            return_result=True,
        )
