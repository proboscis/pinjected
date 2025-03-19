import pytest
from pathlib import Path
from pinjected import Design, EmptyDesign
from pinjected.helper_structure import MetaContext
from pinjected.v2.keys import StrBindKey
from pinjected.v2.async_resolver import AsyncResolver


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