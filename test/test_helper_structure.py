import pytest
import sys
from pathlib import Path
from pinjected import Design, EmptyDesign, design
from pinjected.helper_structure import MetaContext, IdeaRunConfigurations
from pinjected.v2.keys import StrBindKey
from pinjected.v2.async_resolver import AsyncResolver
from pinjected.ide_supports.create_configs import create_idea_configurations


@pytest.mark.asyncio
async def test_a_gather_bindings_with_legacy():
    """Test a_gather_bindings_with_legacy to verify it collects both __meta_design__ and __design__ attributes."""
    # Path to the test file
    test_file = Path(__file__).parent / "test_package/child/module1.py"
    
    # Gather the designs using the new method
    mc = await MetaContext.a_gather_bindings_with_legacy(test_file)
    design = mc.accumulated
    
    # Verify the trace includes both __meta_design__ and __design__ attributes
    meta_design_count = sum(1 for var in mc.trace if var.var_path.endswith("__meta_design__"))
    design_count = sum(1 for var in mc.trace if var.var_path.endswith("__design__"))
    
    # Should find at least one of each type
    assert meta_design_count > 0, "Should find at least one __meta_design__"
    assert design_count > 0, "Should find at least one __design__"
    
    # Print the trace for debugging
    print(f"Found {meta_design_count} __meta_design__ attributes and {design_count} __design__ attributes")
    for i, var in enumerate(mc.trace):
        print(f"  {i}. {var.var_path}")
    
    # Create a resolver for accessing values asynchronously
    resolver = AsyncResolver(design)
    
    # Test that values from both __meta_design__ and __design__ are accessible
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
async def test_a_gather_bindings_legacy_overrides():
    """Test that __design__ attributes take precedence over __meta_design__ with the same keys."""
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
    # Values from __design__ should take precedence over __meta_design__
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
    assert await resolver.provide("special_var") == "from_pinjected_file", "Should get value from child module"
    assert await resolver.provide("design_var") == "from_design_in_pinjected_file", "Should get value from child module"
    
    # Most importantly, verify that __design__ overrides __meta_design__ for shared keys
    assert await resolver.provide("shared_key") == "from_design", "Values from __design__ should override __meta_design__"
    
    # Print all paths to aid debugging
    design_paths = [var.var_path for var in mc.trace]
    print("All var paths:")
    for path in design_paths:
        print(f"  {path}")


@pytest.mark.asyncio
async def test_create_configurations_with_legacy():
    """Test that configuration creation works with both __meta_design__ and __design__ attributes."""
    # Path to test files
    p_root = Path(__file__).parent.parent
    test_file = Path(__file__).parent / "test_package/child/module1.py"
    
    # Create configurations using the a_gather_bindings_with_legacy method
    from pinjected.ide_supports.default_design import pinjected_internal_design
    
    # First gather designs using the new method
    mc = await MetaContext.a_gather_bindings_with_legacy(p_root/"pinjected/ide_supports/create_configs.py")
    
    # Create a design with our test requirements
    test_design = design(
        module_path=test_file,
        interpreter_path=sys.executable
    )
    
    # Create the full design
    full_design = mc.accumulated + test_design + pinjected_internal_design
    
    # Create a resolver with the combined design
    resolver = AsyncResolver(full_design)
    
    # First we need to add print_to_stdout=True to the design
    stdout_design = design(print_to_stdout=True)
    full_design = full_design + stdout_design
    resolver = AsyncResolver(full_design)
    
    # Get the configurations injected object
    configs_injected = create_idea_configurations(wrap_output_with_tag=False)
    
    # When resolved, this will print JSON to stdout instead of returning an object
    configs_result = await resolver[configs_injected]
    
    # Verify that it printed configurations to stdout (None is returned)
    assert configs_result is None, "Should print JSON and return None"
    
    # Verify that the correct design values were used
    meta_config_value = await resolver.provide("meta_config_value")
    additional_config_value = await resolver.provide("additional_config_value")
    
    # Values should come from __design__, which overrides __meta_design__
    assert meta_config_value == "from_design", "meta_config_value should be from __design__"
    assert additional_config_value == "only_in_design", "additional_config_value should be present from __design__"
    
    # Verify that we can access the default_design_paths if it exists
    # In stdout mode, the default_design_paths might be empty because of how the injection works
    # The key point is that we're testing that __design__ values override __meta_design__ values
    default_design_paths = await resolver.provide("default_design_paths")
    print(f"default_design_paths: {default_design_paths}")
    
    # The important thing to verify is that we can access the meta_config_value and additional_config_value
    # and that they are coming from the right places


@pytest.mark.asyncio
async def test_compare_legacy_and_new_method():
    """Test to compare the legacy a_gather_from_path with the new a_gather_bindings_with_legacy method."""
    # Path to test file
    p_root = Path(__file__).parent.parent
    config_path = p_root/"pinjected/ide_supports/create_configs.py"
    
    # Gather designs using both methods
    legacy_context = await MetaContext.a_gather_from_path(config_path)
    new_context = await MetaContext.a_gather_bindings_with_legacy(config_path)
    
    # Create resolvers for both designs
    legacy_resolver = AsyncResolver(legacy_context.accumulated)
    new_resolver = AsyncResolver(new_context.accumulated)
    
    # Check that both resolvers have access to default_design_paths
    legacy_paths = await legacy_resolver.provide("default_design_paths")
    new_paths = await new_resolver.provide("default_design_paths")
    assert legacy_paths == new_paths, "Both methods should have access to default_design_paths"
    
    # Check the meta_config_value - this should be different between the two methods
    legacy_meta_value = await legacy_resolver.provide("meta_config_value")
    new_meta_value = await new_resolver.provide("meta_config_value")
    assert legacy_meta_value == "from_meta_design", "Legacy method should use __meta_design__ value"
    assert new_meta_value == "from_design", "New method should use __design__ value (overriding __meta_design__)"
    
    # Check additional_config_value - this should only be in the new method
    # Legacy method should not have this value
    with pytest.raises(Exception):
        await legacy_resolver.provide("additional_config_value")
    
    # New method should have the additional value
    additional_value = await new_resolver.provide("additional_config_value")
    assert additional_value == "only_in_design", "New method should have access to values only in __design__"
    
    # Compare the trace counts for each method
    legacy_meta_design_count = sum(1 for var in legacy_context.trace if var.var_path.endswith("__meta_design__"))
    new_meta_design_count = sum(1 for var in new_context.trace if var.var_path.endswith("__meta_design__"))
    new_design_count = sum(1 for var in new_context.trace if var.var_path.endswith("__design__"))
    
    print(f"Legacy method found {legacy_meta_design_count} __meta_design__ attributes")
    print(f"New method found {new_meta_design_count} __meta_design__ attributes and {new_design_count} __design__ attributes")
    
    # Verify that the new method finds more attributes
    assert new_meta_design_count + new_design_count > legacy_meta_design_count, \
        "New method should find more attributes than legacy method"