from pathlib import Path

import pytest
from returns.maybe import Nothing

from pinjected import DesignSpec, SimpleBindSpec
from pinjected.helper_structure import SpecTrace, MetaContext
from pinjected.v2.keys import StrBindKey


@pytest.mark.asyncio
async def test_design_spec_empty():
    """Test that empty DesignSpec behaves correctly."""
    empty_spec = DesignSpec.empty()
    assert empty_spec.get_spec(StrBindKey("any_key")) is Nothing


@pytest.mark.asyncio
async def test_design_spec_get_spec():
    """Test that DesignSpec can retrieve specifications for keys."""
    # Create a DesignSpec with a known binding
    test_spec = DesignSpec.new(
        test_key=SimpleBindSpec(
            validator=lambda item: "test_key must be int" if not isinstance(item, int) else None,
            documentation="This is a test key"
        )
    )
    
    # Test that we can retrieve the spec
    spec = test_spec.get_spec(StrBindKey("test_key"))
    assert spec is not Nothing, "Should find the spec for test_key"
    
    # Test that non-existent keys return Nothing
    assert test_spec.get_spec(StrBindKey("non_existent")) is Nothing


@pytest.mark.asyncio
async def test_design_spec_addition():
    """Test that DesignSpec addition combines specs correctly."""
    # Create two specs with different keys
    spec1 = DesignSpec.new(
        key1=SimpleBindSpec(documentation="Spec 1")
    )
    
    spec2 = DesignSpec.new(
        key2=SimpleBindSpec(documentation="Spec 2")
    )
    
    # Combine them
    combined = spec1 + spec2
    
    # Test that both keys are accessible
    assert combined.get_spec(StrBindKey("key1")) is not Nothing
    assert combined.get_spec(StrBindKey("key2")) is not Nothing
    
    # Test that specs are retrieved from the correct source
    key1_spec = combined.get_spec(StrBindKey("key1")).unwrap()
    key2_spec = combined.get_spec(StrBindKey("key2")).unwrap()
    
    assert key1_spec.spec_doc_provider is not Nothing
    assert key2_spec.spec_doc_provider is not Nothing
    
    # When resolved, they should provide the correct documentation
    key1_doc_provider = key1_spec.spec_doc_provider.unwrap()
    key2_doc_provider = key2_spec.spec_doc_provider.unwrap()
    
    key1_doc = await key1_doc_provider(StrBindKey("key1"))
    key2_doc = await key2_doc_provider(StrBindKey("key2"))
    
    # The result is a FutureResult[IOSuccess[str]], so we need to use .unwrap() to get the IO and then to check its value
    from returns.unsafe import unsafe_perform_io
    assert unsafe_perform_io(key1_doc.unwrap()) == "Spec 1"
    assert unsafe_perform_io(key2_doc.unwrap()) == "Spec 2"


@pytest.mark.asyncio
async def test_design_spec_precedence():
    """Test that when specs are combined, the leftmost one takes precedence for duplicate keys."""
    # Create two specs with the same key but different validators and documentation
    spec1 = DesignSpec.new(
        shared_key=SimpleBindSpec(
            validator=lambda item: "must be int" if not isinstance(item, int) else None,
            documentation="Spec 1 documentation"
        )
    )
    
    spec2 = DesignSpec.new(
        shared_key=SimpleBindSpec(
            validator=lambda item: "must be str" if not isinstance(item, str) else None,
            documentation="Spec 2 documentation"
        )
    )
    
    # Combine them with spec1 taking precedence
    combined = spec1 + spec2
    
    # The shared_key should have spec1's validator and documentation
    shared_key_spec = combined.get_spec(StrBindKey("shared_key"))
    assert shared_key_spec is not Nothing
    
    # Unwrap the Some[BindSpec] to get the actual BindSpec
    shared_key_bind_spec = shared_key_spec.unwrap()
    
    # Check that the documentation is from spec1
    doc_provider = shared_key_bind_spec.spec_doc_provider.unwrap()
    doc = await doc_provider(StrBindKey("shared_key"))
    from returns.unsafe import unsafe_perform_io
    assert unsafe_perform_io(doc.unwrap()) == "Spec 1 documentation"
    
    # For validator testing, we'll need to create a test SimpleBindSpec and check the validator
    # Verifying that the validator property is from spec1 
    # (In this case we can only verify that the validator exists, not its exact behavior)
    assert shared_key_bind_spec.validator is not Nothing


@pytest.mark.asyncio
async def test_a_gather_design_spec_from_path():
    """Test that SpecTrace.a_gather_from_path collects __design_spec__ attributes."""
    # Path to the test file with __design_spec__
    test_file = Path(__file__).parent / "test_package/__pinjected__.py"
    
    # Gather the specs
    spec_trace = await SpecTrace.a_gather_from_path(test_file)
    accumulated_spec = spec_trace.accumulated
    
    # Verify that we found at least one spec
    assert len(spec_trace.trace) > 0, "Should find at least one __design_spec__"
    
    # Print the trace for debugging
    print(f"Found {len(spec_trace.trace)} __design_spec__ attributes")
    for i, var in enumerate(spec_trace.trace):
        print(f"  {i}. {var.var_path}")
    
    # Verify that the design_name key has a spec
    design_name_spec = accumulated_spec.get_spec(StrBindKey("design_name"))
    assert design_name_spec is not Nothing, "Should find a spec for design_name"
    
    # Unwrap the Some[BindSpec] to get the actual BindSpec
    design_name_bind_spec = design_name_spec.unwrap()
    
    # Test the validator - it should validate that design_name is a string
    assert design_name_bind_spec.validator is not Nothing
    
    # Check the documentation
    doc_provider = design_name_bind_spec.spec_doc_provider.unwrap()
    doc = await doc_provider(StrBindKey("design_name"))
    from returns.unsafe import unsafe_perform_io
    assert unsafe_perform_io(doc.unwrap()) == "This is a test design spec"


@pytest.mark.asyncio
async def test_meta_context_includes_design_spec():
    """Test that MetaContext.a_gather_bindings_with_legacy also gathers design specs."""
    # Path to the test file
    test_file = Path(__file__).parent / "test_package/__pinjected__.py"
    
    # Gather designs and specs
    mc = await MetaContext.a_gather_bindings_with_legacy(test_file)
    
    # Verify that spec_trace is populated
    assert mc.spec_trace is not None
    assert len(mc.spec_trace.trace) > 0, "Should find at least one __design_spec__"
    
    # Verify that we can access the accumulated spec
    accumulated_spec = mc.spec_trace.accumulated
    assert accumulated_spec.get_spec(StrBindKey("design_name")) is not Nothing
    
    # Print the spec trace for debugging
    print(f"Found {len(mc.spec_trace.trace)} specs in MetaContext")
    for i, var in enumerate(mc.spec_trace.trace):
        print(f"  {i}. {var.var_path}")


@pytest.mark.asyncio
async def test_multi_level_design_spec_hierarchy():
    """Test that design specs are properly collected from a hierarchy of modules."""
    # Path to a module in the child directory
    test_file = Path(__file__).parent / "test_package/child/module1.py"
    
    # For this test we need to get specs from each location manually
    import sys
    from pinjected.module_helper import walk_module_with_special_files
    from pinjected.module_var_path import ModuleVarPath
    
    # Verify that we find specs from both levels
    specs_found = []
    
    for var in walk_module_with_special_files(test_file, attr_names=["__design_spec__"],
                                              special_filenames=["__pinjected__.py"]):
        specs_found.append(var.var_path)
    
    # Print the specs found
    print(f"Found design specs: {specs_found}")
    
    # Check that we found specs from both levels
    found_top_level = any('test_package.__pinjected__' in spec_path for spec_path in specs_found)
    found_child_level = any('test_package.child.__pinjected__' in spec_path for spec_path in specs_found)
    
    assert found_top_level, "Should find __design_spec__ from top level"
    assert found_child_level, "Should find __design_spec__ from child level"
    
    # Directly load and test the specs
    from pinjected.v2.keys import StrBindKey
    
    # Load the top-level spec
    from test.test_package.__pinjected__ import __design_spec__ as top_spec
    # Load the child-level spec
    from test.test_package.child.__pinjected__ import __design_spec__ as child_spec
    
    # Test that we can get specs from both levels
    design_name_spec = top_spec.get_spec(StrBindKey("design_name"))
    assert design_name_spec is not Nothing, "Should find spec for design_name from top level"
    
    design_var_spec = child_spec.get_spec(StrBindKey("design_var"))
    assert design_var_spec is not Nothing, "Should find spec for design_var from child level"
    
    # Manually create a merged spec to test precedence
    merged_spec = child_spec + top_spec  # Child takes precedence
    
    # Verify that shared keys use the child's value
    shared_key_spec = merged_spec.get_spec(StrBindKey("shared_key"))
    assert shared_key_spec is not Nothing, "Should find spec for shared_key"
    
    # Check some properties of the specs
    design_name_bind_spec = design_name_spec.unwrap()
    assert design_name_bind_spec.validator is not Nothing
    
    design_var_bind_spec = design_var_spec.unwrap()
    assert design_var_bind_spec.validator is not Nothing
    
    # Check documentation
    from returns.unsafe import unsafe_perform_io
    doc_provider = design_var_bind_spec.spec_doc_provider.unwrap()
    doc = await doc_provider(StrBindKey("design_var"))
    assert "Child module" in unsafe_perform_io(doc.unwrap()), "Should have documentation from child directory"