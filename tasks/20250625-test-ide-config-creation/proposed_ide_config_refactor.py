"""Proposed refactoring of IDE config creation to work with pinjected run.

This shows how we could refactor create_idea_configurations to work better
with the standard pinjected run command instead of meta_main.
"""

from pathlib import Path
from pinjected import injected, design, IProxy, Injected
from beartype import beartype
import json
import sys


# Current problematic approach that requires meta_main
@injected
@beartype
def create_idea_configurations_old(
    inspect_and_make_configurations,
    module_path: Path,  # Positional dependency - hard to pass via CLI
    print_to_stdout,
    /,
    wrap_output_with_tag=True,
):
    """Current implementation that doesn't work well with pinjected run."""
    # ... implementation ...
    pass


# Proposed approach 1: Use IProxy for CLI-friendly interface
create_idea_configurations_cli: IProxy = Injected.bind(
    create_idea_configurations_old,
    # Get module_path from command line args or environment
    module_path=Injected.pure(
        lambda: Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    ),
    print_to_stdout=Injected.pure(True),
)


# Proposed approach 2: Wrapper function that's CLI-friendly
@injected
def create_idea_configurations_for_file(
    create_idea_configurations_old,
    /,
    file_path: str,  # Regular parameter that can be passed via CLI
    output_format: str = "json",
    wrap_with_tags: bool = True,
):
    """CLI-friendly wrapper that can be called via pinjected run."""
    return create_idea_configurations_old(
        module_path=Path(file_path),
        wrap_output_with_tag=wrap_with_tags,
    )


# Proposed approach 3: Context-aware version
@injected
def create_idea_configurations_contextual(
    inspect_and_make_configurations,
    print_to_stdout,
    current_module_path,  # Injected from context
    /,
    wrap_output_with_tag: bool = True,
):
    """Version that gets module_path from injection context."""
    configs = inspect_and_make_configurations(current_module_path)
    # ... rest of implementation ...


# Proposed approach 4: Dedicated IDE commands module
@injected
def ide_create_configs(
    # No positional-only params needed here
    module: str,  # Module path as string for CLI
    design_path: str = "pinjected.ide_supports.default_design.pinjected_internal_design",
    format: str = "json",
    output: str = "stdout",  # stdout, file, return
):
    """New dedicated command for IDE integration.
    
    Usage:
        pinjected run pinjected.ide_supports.commands.ide_create_configs \
            --module /path/to/module.py \
            --design-path my.custom.design \
            --format json \
            --output stdout
    """
    from pinjected.helper_structure import MetaContext
    from pinjected.run_helpers.run_injected import run_injected
    import asyncio

    # Load the module context
    module_path = Path(module)
    meta_context = asyncio.run(MetaContext.a_gather_bindings_with_legacy(module_path))

    # Run the actual configuration creation
    result = run_injected(
        "get",
        "pinjected.ide_supports.create_configs.create_idea_configurations",
        design_path,
        return_result=True,
        overrides=design(
            module_path=module_path,
            print_to_stdout=(output == "stdout"),
            wrap_output_with_tag=True,
        )
        + meta_context.final_design,
    )

    if output == "file":
        output_path = module_path.with_suffix(".pinjected-configs.json")
        output_path.write_text(json.dumps(result))
        print(f"Configurations written to: {output_path}")
    elif output == "return":
        return result
    # stdout is handled by create_idea_configurations itself


# Example of how IDE plugins would use the new approach:
"""
# Old way (deprecated):
python -m pinjected.meta_main pinjected.ide_supports.create_configs.create_idea_configurations /path/to/module.py

# New way (option 1 - using wrapper):
pinjected run pinjected.ide_supports.create_configs.create_idea_configurations_for_file --file-path /path/to/module.py

# New way (option 2 - using dedicated command):
pinjected run pinjected.ide_supports.commands.ide_create_configs --module /path/to/module.py

# New way (option 3 - using IProxy):
pinjected run pinjected.ide_supports.create_configs.create_idea_configurations_cli /path/to/module.py

# Future: Dedicated pinjected subcommand
pinjected ide create-configs /path/to/module.py
"""
