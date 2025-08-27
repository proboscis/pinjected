#!/usr/bin/env python3
"""Test script to replicate PyCharm plugin's pinjected-indexer integration"""

import subprocess
import json
import time
from pathlib import Path


def run_command(cmd, cwd=None, timeout=30):
    """Run command and capture output, mimicking PyCharm plugin behavior"""
    print(f"[DEBUG] Running command: {' '.join(cmd)}")
    print(f"[DEBUG] Working directory: {cwd or 'current'}")

    try:
        result = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout
        )

        if result.stdout:
            print(f"[DEBUG] stdout:\n{result.stdout}")
        if result.stderr:
            print(f"[DEBUG] stderr:\n{result.stderr}")
        print(f"[DEBUG] Exit code: {result.returncode}")

        return result
    except subprocess.TimeoutExpired:
        print(f"[DEBUG] Command timed out after {timeout} seconds")
        return None
    except Exception as e:
        print(f"[DEBUG] Error running command: {e}")
        return None


def check_indexer_update(project_root):
    """Check the update command"""
    print("\n=== Testing pinjected-indexer update ===")

    # First check which binary is being used
    which_result = run_command(["which", "pinjected-indexer"])
    if which_result:
        print(f"[INFO] Using indexer at: {which_result.stdout.strip()}")

    # Check version/help to see available commands
    print("\n--- Checking available commands ---")
    run_command(["pinjected-indexer", "--help"])

    # Try the update command (mimicking auto-refresh)
    print("\n--- Testing update command (auto-refresh) ---")
    result = run_command(
        ["pinjected-indexer", "--root", project_root, "update", "--quick"],
        cwd=project_root,
        timeout=10,
    )

    # Try the update command (manual refresh)
    print("\n--- Testing update command (manual refresh) ---")
    result = run_command(
        ["pinjected-indexer", "--root", project_root, "update"],
        cwd=project_root,
        timeout=30,
    )

    return result is not None and result.returncode == 0


def check_query_functions(project_root, type_name):
    """Check querying for functions matching a type"""
    print(f"\n=== Testing query for type '{type_name}' ===")

    result = run_command(
        [
            "pinjected-indexer",
            "--root",
            project_root,
            "query-iproxy-functions",
            type_name,
        ],
        cwd=project_root,
    )

    if result and result.returncode == 0:
        try:
            functions = json.loads(result.stdout)
            print(f"[INFO] Found {len(functions)} matching functions:")
            for func in functions:
                print(f"  - {func['function_name']} in {func['module_path']}")
                # Check if module path has the old format
                if func["module_path"].startswith(".Users."):
                    print(f"    WARNING: Old module path format detected!")
            return functions
        except json.JSONDecodeError as e:
            print(f"[ERROR] Failed to parse JSON: {e}")
            print(f"[ERROR] Raw output: {result.stdout}")
    return []


def main():
    # Test with sge-hub project
    project_root = "/Users/s22625/repos/sge-hub"

    print(f"Testing pinjected-indexer integration")
    print(f"Project root: {project_root}")
    print("=" * 60)

    # Test update command
    update_success = check_indexer_update(project_root)

    if not update_success:
        print("\n[ERROR] Update command failed!")
        print("[INFO] Trying to update the binary in PATH...")

        # Try to fix by copying the new binary
        new_binary = (
            Path.home() / "Library/Application Support/pinjected/pinjected-indexer"
        )
        if new_binary.exists():
            print(f"[INFO] Found new binary at: {new_binary}")
            run_command(
                ["cp", str(new_binary), "/Users/s22625/.local/bin/pinjected-indexer"]
            )
            print("[INFO] Updated binary in PATH, retrying...")
            update_success = check_indexer_update(project_root)

    # Test querying functions
    test_types = ["int", "User", "Product"]
    for type_name in test_types:
        functions = check_query_functions(project_root, type_name)
        time.sleep(0.5)  # Small delay between queries

    print("\n" + "=" * 60)
    print("Test completed!")

    # Final check of module path format
    print("\n=== Module Path Format Check ===")
    functions = check_query_functions(project_root, "int")
    if functions:
        sample = functions[0] if functions else None
        if sample:
            if sample["module_path"].startswith(".Users."):
                print("[ERROR] Module paths still have old format!")
                print("[ERROR] Example:", sample["module_path"])
                print(
                    "[ERROR] Should be like: sge_hub.dataset_creation.converter.a_feature"
                )
            else:
                print("[OK] Module paths have correct format")
                print("[OK] Example:", sample["module_path"])


if __name__ == "__main__":
    main()
