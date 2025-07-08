#!/usr/bin/env python3
"""Replace eval_injected with proper resolver pattern."""

import re


def fix_eval_injected(file_path):
    """Replace eval_injected pattern with resolver pattern."""
    with open(file_path, "r") as f:
        content = f.read()

    # Add resolver import at the top if not present
    if "from pinjected.v2.async_resolver import AsyncResolver" not in content:
        # Find position after other imports
        lines = content.split("\n")
        import_pos = None
        for i, line in enumerate(lines):
            if line.startswith("from pinjected"):
                import_pos = i + 1
                break
        if import_pos:
            lines.insert(
                import_pos, "from pinjected.v2.async_resolver import AsyncResolver"
            )
            content = "\n".join(lines)

    # Replace the pattern for eval_injected
    # Pattern 1: with design(): block
    pattern1 = r"with design\(\):\s*\n\s*from pinjected import eval_injected\s*\n\s*assert eval_injected\(([^)]+)\) == ([^\n]+)"
    replacement1 = """d = design()
        resolver = AsyncResolver(d)
        blocking = resolver.to_blocking()
        assert blocking.provide(\\1) == \\2"""

    content = re.sub(pattern1, replacement1, content)

    # Pattern 2: standalone eval_injected calls
    pattern2 = (
        r"from pinjected import eval_injected\s*\n\s*result = eval_injected\(([^)]+)\)"
    )
    replacement2 = """resolver = AsyncResolver(design())
        blocking = resolver.to_blocking()
        result = blocking.provide(\\1)"""

    content = re.sub(pattern2, replacement2, content)

    # Pattern 3: await eval_injected
    pattern3 = r"from pinjected import eval_injected\s*\n\s*result = await eval_injected\(([^)]+)\)"
    replacement3 = """resolver = AsyncResolver(design())
        result = await resolver.provide(\\1)"""

    content = re.sub(pattern3, replacement3, content)

    # Pattern 4: assert eval_injected without from import
    pattern4 = r"assert eval_injected\(([^)]+)\) == ([^\n]+)"
    replacement4 = "assert blocking.provide(\\1) == \\2"

    content = re.sub(pattern4, replacement4, content)

    # Write back
    with open(file_path, "w") as f:
        f.write(content)


# Fix the file
fix_eval_injected("test/test_di_injected_operators.py")
print("Fixed test/test_di_injected_operators.py")
