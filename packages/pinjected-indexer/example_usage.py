#!/usr/bin/env python3
"""
Example showing how to use pinjected-indexer from Python code.
This could be integrated into an IDE plugin.
"""

import json
import subprocess
from typing import List, Dict, Any


def find_iproxy_functions(
    type_name: str, project_root: str = "."
) -> List[Dict[str, Any]]:
    """Find @injected functions that can work with IProxy[type_name]."""
    try:
        # Run with log level = error to suppress info logs
        result = subprocess.run(
            [
                "pinjected-indexer",
                "--root",
                project_root,
                "--log-level",
                "error",
                "query-iproxy-functions",
                type_name,
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        # Parse JSON output
        json_str = result.stdout.strip()

        if json_str:
            return json.loads(json_str)
        return []

    except subprocess.CalledProcessError as e:
        print(f"Error querying indexer: {e}")
        return []
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        return []


def main():
    """Example usage."""
    # Example 1: Find functions for User type
    print("Finding functions for IProxy[User]...")
    user_functions = find_iproxy_functions("User")

    for func in user_functions:
        print(f"  📦 {func['function_name']}")
        print(f"     Module: {func['module_path']}")
        print(f"     File: {func['file_path']}:{func['line_number']}")
        if func.get("docstring"):
            print(f"     Docs: {func['docstring']}")
        print()

    # Example 2: Find functions for generic types
    print("\nFinding functions for IProxy[List[User]]...")
    list_functions = find_iproxy_functions("List[User]")

    for func in list_functions:
        print(f"  📦 {func['function_name']}")
        print(f"     Parameter: {func['parameter_name']}: {func['parameter_type']}")
        print()

    # Example 3: Generate CLI command for calling a function
    if user_functions:
        func = user_functions[0]
        print("\nTo call this function with an IProxy object:")
        print(f"  pinjected call {func['module_path']} my_module.user_proxy")


if __name__ == "__main__":
    main()
