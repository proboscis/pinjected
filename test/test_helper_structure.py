import sys
from pathlib import Path

import pytest

from pinjected import design
from pinjected.helper_structure import MetaContext
from pinjected.v2.async_resolver import AsyncResolver
from pinjected.v2.keys import StrBindKey


@pytest.mark.asyncio
async def test_a_gather_bindings_with_legacy():
    """Test a_gather_bindings_with_legacy to verify it collects __design__ attributes."""
    # Path to the test file
    test_file = Path(__file__).parent / "test_package/child/module1.py"

    # Gather the designs using the method
    mc = await MetaContext.a_gather_bindings_with_legacy(test_file)
    design = mc.accumulated

    # Verify the trace includes __design__ attributes
    design_count = sum(1 for var in mc.trace if var.var_path.endswith("__design__"))

    # Should find at least one __design__
    assert design_count > 0, "Should find at least one __design__"

    # Print the trace for debugging
    print(f"Found {design_count} __design__ attributes")
    for i, var in enumerate(mc.trace):
        print(f"  {i}. {var.var_path}")

    # Create a resolver for accessing values asynchronously
    resolver = AsyncResolver(design)

    # Test that values from __design__ are accessible
    special_var = await resolver.provide("special_var")
    design_var = await resolver.provide("design_var")
    meta_name = await resolver.provide("meta_name")
    design_name = await resolver.provide("design_name")

    assert special_var == "from_pinjected_file"
    assert design_var == "from_design_in_pinjected_file"

    # Check the ordering of attributes based on the attr_names parameter
    # Values from child/__pinjected__.py should take precedence over top-level
    assert meta_name == "test_package.child.__pinjected__"
    assert design_name == "test_package.child.__pinjected__"

    # Print all bindings for debugging
    print("All bindings in accumulated design:")
    for key in design.bindings:
        print(f"  {key}")


@pytest.mark.asyncio
async def test_a_gather_bindings_precedence():
    """Test that __design__ attributes follow proper precedence rules."""
    # Create a file path for testing
    test_file = Path(__file__).parent / "test_package/child/module1.py"

    # Gather the designs
    mc = await MetaContext.a_gather_bindings_with_legacy(test_file)
    design = mc.accumulated

    # Create a resolver for accessing values asynchronously
    resolver = AsyncResolver(design)

    # Print all design bindings for debugging
    print("All bindings in accumulated design:")
    for key in design.bindings:
        value = await resolver.provide(key)
        print(f"  {key}: {value}")

    # Test the precedence of attributes
    # Values from __pinjected__.py should take precedence over module attributes
    # Values from child/ should take precedence over parent values

    # Create StrBindKey objects for our test keys
    special_var_key = StrBindKey("special_var")
    design_var_key = StrBindKey("design_var")
    shared_key_key = StrBindKey("shared_key")

    # Verify attributes exist
    assert special_var_key in design.bindings, "special_var should be in bindings"
    assert design_var_key in design.bindings, "design_var should be in bindings"
    assert shared_key_key in design.bindings, "shared_key should be in bindings"

    # Verify values match expected precedence
    assert await resolver.provide("special_var") == "from_pinjected_file", (
        "Should get value from child module"
    )
    assert await resolver.provide("design_var") == "from_design_in_pinjected_file", (
        "Should get value from child module"
    )

    # Verify that we get the expected value for shared_key
    assert await resolver.provide("shared_key") == "from_design", (
        "Should get value from __design__"
    )

    # Print all paths to aid debugging
    design_paths = [var.var_path for var in mc.trace]
    print("All var paths:")
    for path in design_paths:
        print(f"  {path}")


@pytest.mark.asyncio
async def test_create_configurations_with_design():
    """Test that configuration creation works with __design__ attributes."""
    # Path to test files
    p_root = Path(__file__).parent.parent
    test_file = Path(__file__).parent / "test_package/child/module1.py"

    # Create configurations using the a_gather_bindings_with_legacy method
    from pinjected.ide_supports.default_design import pinjected_internal_design

    # First gather designs using the method
    mc = await MetaContext.a_gather_bindings_with_legacy(
        p_root / "pinjected/ide_supports/create_configs.py"
    )

    # Create a design with our test requirements
    test_design = design(
        module_path=test_file,
        interpreter_path=sys.executable,
        default_design_paths=[],  # Add required dependency
    )

    # Create the full design with print_to_stdout=True and __pinjected__wrap_output_with_tag=False
    full_design = (
        mc.accumulated
        + test_design
        + pinjected_internal_design
        + design(print_to_stdout=True)
        + design(__pinjected__wrap_output_with_tag=False)
    )

    # Create a resolver with the combined design
    resolver = AsyncResolver(full_design)

    # Now resolve create_idea_configurations through the resolver
    # When resolved with print_to_stdout=True, this will print JSON to stdout instead of returning an object
    configs_result = await resolver.provide("create_idea_configurations")

    # Verify that it printed configurations to stdout (None is returned)
    assert configs_result is None, "Should print JSON and return None"

    # Verify that the correct design values were used
    meta_config_value = await resolver.provide("meta_config_value")
    additional_config_value = await resolver.provide("additional_config_value")

    # Values should come from __design__
    assert meta_config_value == "from_design", (
        "meta_config_value should be from __design__"
    )
    assert additional_config_value == "only_in_design", (
        "additional_config_value should be present from __design__"
    )

    # Verify that we can access the default_design_paths if it exists
    # In stdout mode, the default_design_paths might be empty because of how the injection works
    default_design_paths = await resolver.provide("default_design_paths")
    print(f"default_design_paths: {default_design_paths}")

    # The important thing to verify is that we can access the meta_config_value and additional_config_value
    # and that they are coming from the right places


# Test comparing legacy and new methods removed since __meta_design__ is deprecated
# and a_gather_from_path is also deprecated
