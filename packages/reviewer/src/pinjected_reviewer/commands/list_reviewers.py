"""
Command to list all reviewer definitions.
"""
import argparse
import asyncio
from pathlib import Path

from pinjected import AsyncResolver, instances
from pinjected.helper_structure import MetaContext
from pinjected_reviewer.loader import reviewer_definitions

async def list_reviewers(repo_path: Path):
    """
    List all reviewer definitions found in the repository.
    
    Args:
        repo_path: Path to the repository root
    """
    current_file = Path(__file__)
    
    mc = await MetaContext.a_gather_bindings_with_legacy(current_file)
    d = await mc.a_final_design
    
    d = d + instances(repo_root=repo_path)
    
    resolver = AsyncResolver(d)
    definitions = await resolver.provide(reviewer_definitions)
    
    if not definitions:
        print(f"No reviewer definitions found in {repo_path / '.reviewers'}")
        return
    
    print(f"Found {len(definitions)} reviewer definitions:")
    for i, definition in enumerate(definitions, 1):
        print(f"\n{i}. {definition.name}")
        print(f"   File: {definition.file_path.name}")
        print(f"   Trigger: {definition.trigger_condition}")
        print(f"   Return Type: {definition.return_type}")
