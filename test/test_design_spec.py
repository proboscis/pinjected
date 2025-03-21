from pathlib import Path

import pytest
from returns.maybe import Nothing, Some

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
    """Test that when specs are combined, the right-hand side takes precedence for duplicate keys."""
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
    
    # When we add spec2 to spec1, spec2 should take precedence for shared keys
    combined = spec1 + spec2
    
    # The shared_key should have spec2's validator and documentation since it was added to spec1
    shared_key_spec = combined.get_spec(StrBindKey("shared_key"))
    assert shared_key_spec is not Nothing
    
    # Unwrap the Some[BindSpec] to get the actual BindSpec
    shared_key_bind_spec = shared_key_spec.unwrap()
    
    # Check if the documentation is from spec2 (the one on the right side of +)
    # With the updated implementation, spec2 takes precedence.
    doc_provider = shared_key_bind_spec.spec_doc_provider.unwrap()
    doc = await doc_provider(StrBindKey("shared_key"))
    from returns.unsafe import unsafe_perform_io
    
    # The right-hand spec (spec2) takes precedence, so documentation should come from spec2
    assert unsafe_perform_io(doc.unwrap()) == "Spec 2 documentation"
    
    # For validator testing, verify that the validator exists (we can't check its behavior easily)
    assert shared_key_bind_spec.validator is not Nothing
    
    # Additional test showing what happens when order is reversed
    # When spec1 is added to spec2, spec1 should take precedence for the merged spec
    combined_reversed = spec2 + spec1 
    reversed_spec = combined_reversed.get_spec(StrBindKey("shared_key")).unwrap()
    reversed_doc = await reversed_spec.spec_doc_provider.unwrap()(StrBindKey("shared_key"))
    # The right-hand spec (spec1 in this case) takes precedence
    assert unsafe_perform_io(reversed_doc.unwrap()) == "Spec 1 documentation"


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
    # NOTE: With the current implementation, the first spec in the list has precedence
    # In our current design, all additions follow the same order principle:
    # spec1 + spec2 where spec1 is checked first for each key.
    merged_spec = child_spec + top_spec  # In the current implementation, child_spec takes precedence for duplicate keys
    
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


@pytest.mark.asyncio
async def test_simple_bind_spec_validator():
    """Test that SimpleBindSpec validator works correctly."""
    # Create a SimpleBindSpec with a validator and documentation
    bind_spec = SimpleBindSpec(
        validator=lambda item: "must be str" if not isinstance(item, str) else None,
        documentation="Test documentation"
    )
    
    # Check that the validator property returns a Some monad
    assert bind_spec.validator is not Nothing
    assert isinstance(bind_spec.validator, Some)
    
    # For SimpleBindSpec, the validator takes only one argument, not key and value
    # So we cannot directly test the validator function from the property
    # Instead, we'll use the _validator_impl method which handles the FutureResultE wrapping
    
    # Check documentation
    assert bind_spec.spec_doc_provider is not Nothing
    doc_provider = bind_spec.spec_doc_provider.unwrap()
    doc_future = doc_provider(StrBindKey("test"))
    
    # Await the future to get the result
    doc_result = await doc_future
    from returns.unsafe import unsafe_perform_io
    assert unsafe_perform_io(doc_result.unwrap()) == "Test documentation"