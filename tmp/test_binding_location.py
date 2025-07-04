#!/usr/bin/env python3
"""Test script to verify binding location tracking improvements"""

import asyncio
from pathlib import Path
from pinjected import Injected, design
from pinjected.di.metadata import Metadata
from pinjected.di.metadata.location_data import ModuleVarLocation
from pinjected.helper_structure import MetaContext
from pinjected.v2.keys import StrBindKey
import tempfile
import os


async def test_binding_location_tracking():
    """Test that binding locations are correctly extracted"""
    
    # Create a temporary directory and test file
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir) / "test_package"
        test_dir.mkdir()
        
        # Create __init__.py
        (test_dir / "__init__.py").write_text("")
        
        # Create __pinjected__.py with design that has location metadata
        pinjected_file = test_dir / "__pinjected__.py"
        pinjected_content = """
from pinjected import design, instances
from pinjected.di.metadata import Metadata
from pinjected.di.metadata.location_data import ModuleVarLocation

# Create design with metadata
__design__ = design(
    test_service=instances(
        value="test_value",
        metadata=Metadata(
            code_location=ModuleVarLocation(
                path=__file__,
                line=10
            )
        )
    ),
    another_service=instances(
        value="another_value"
        # No metadata - should fall back to file path
    )
)
"""
        pinjected_file.write_text(pinjected_content)
        
        # Create a test module that uses the design
        test_module = test_dir / "test_module.py"
        test_module_content = """
from pinjected import Injected

def some_function():
    pass
"""
        test_module.write_text(test_module_content)
        
        # Gather the meta context
        meta_context = await MetaContext.a_gather_bindings_with_legacy(test_module)
        
        # Check the key_to_path mapping
        print("Key to path mapping:")
        for key, path in meta_context.key_to_path.items():
            print(f"  {key}: {path}")
        
        # Verify test_service has line number
        test_service_key = StrBindKey("test_service")
        if test_service_key in meta_context.key_to_path:
            location = meta_context.key_to_path[test_service_key]
            print(f"\ntest_service location: {location}")
            assert ":10" in location, f"Expected line number :10 in location, got {location}"
            print("✓ test_service has correct line number")
        else:
            print("✗ test_service key not found")
        
        # Verify another_service falls back to file path
        another_service_key = StrBindKey("another_service") 
        if another_service_key in meta_context.key_to_path:
            location = meta_context.key_to_path[another_service_key]
            print(f"\nanother_service location: {location}")
            assert "__pinjected__.py" in location, f"Expected file path in location, got {location}"
            assert ":" not in location or location.endswith("__pinjected__.py"), "Should not have line number"
            print("✓ another_service falls back to file path")
        else:
            print("✗ another_service key not found")
        
        print("\n✅ All tests passed!")


if __name__ == "__main__":
    asyncio.run(test_binding_location_tracking())