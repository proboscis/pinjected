#!/usr/bin/env python3
"""Fix operator tests to check for DelegatedVar instead of Injected."""

import re


def fix_operator_tests(file_path):
    """Fix isinstance checks for operator results."""
    with open(file_path, "r") as f:
        content = f.read()

    # Add import if not present
    if "from pinjected.di.proxiable import DelegatedVar" not in content:
        # Find the right place to add import (after other imports)
        lines = content.split("\n")
        import_added = False
        for i, line in enumerate(lines):
            if line.startswith("from pinjected import"):
                lines.insert(i + 1, "from pinjected.di.proxiable import DelegatedVar")
                import_added = True
                break
        if import_added:
            content = "\n".join(lines)

    # Replace isinstance checks
    content = re.sub(
        r"assert isinstance\((result|res|output|merged|negated|unpacked|attrs|added|subtracted|multiplied|divided|floordivided|remaindered|powered|and_result|or_result|xor_result|eq_result|ne_result|lt_result|le_result|gt_result|ge_result|lshifted|rshifted|matmul_result), Injected\)",
        r"assert isinstance(\1, DelegatedVar)",
        content,
    )

    with open(file_path, "w") as f:
        f.write(content)


# Fix the test file
fix_operator_tests("test/test_di_injected_operators.py")
print("Fixed test/test_di_injected_operators.py")
