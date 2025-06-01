#!/usr/bin/env python3

from pinjected import design, injected
from pinjected.cli_visualizations.tree import design_rich_tree


@injected
def test_function(dependency: str):
    return f"Result: {dependency}"


test_design = design(dependency="test_value", test_target=test_function)

print("Testing dependency graph visualization with special keys...")
try:
    tree_output = design_rich_tree(test_design, test_function)
    print("✓ Successfully created dependency tree without 'not found' errors")
    print("Tree output preview:")
    print(
        str(tree_output)[:200] + "..."
        if len(str(tree_output)) > 200
        else str(tree_output)
    )
except Exception as e:
    print(f"✗ Error: {e}")
    raise

print("\nTest completed successfully!")
